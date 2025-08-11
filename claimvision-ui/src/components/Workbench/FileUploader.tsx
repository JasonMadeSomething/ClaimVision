"use client";

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';
import { ArrowUpTrayIcon, XMarkIcon } from '@heroicons/react/24/outline';
import UploadPlaceholderCard from './UploadPlaceholderCard';
import { useWebSocket } from '@/context/WebSocketContext';

interface UploadedFileRef {
  id?: string;
  file_id?: string;
  file_name: string;
  status?: FileStatus;
  url?: string;
}

interface FileUploaderProps {
  claimId: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onUploadComplete: (newFiles: any[]) => void;
  maxFileSize?: number; // in bytes, default 10MB
  maxFiles?: number; // default 10
  authToken: string;
  roomId?: string;
  showPlaceholderCards?: boolean;
}

// Maximum size for a single upload batch in bytes (5MB)
const MAX_BATCH_SIZE = 5 * 1024 * 1024;

// Status for file processing
type FileStatus = 'pending' | 'uploading' | 'uploaded' | 'processed' | 'failed' | 'analyzed' | 'skipped_analysis' | 'error';

interface FileWithStatus {
  file: File;
  status: FileStatus;
  progress: number;
  id?: string;
  error?: string;
}

export default function FileUploader({
  claimId,
  onUploadComplete,
  maxFileSize = 10 * 1024 * 1024, // 10MB default
  maxFiles = 10,
  authToken,
  roomId,
  showPlaceholderCards = false
}: FileUploaderProps) {
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Track active batch IDs for websocket correlation
  const activeBatchIdsRef = useRef<Set<string>>(new Set());
  // Map fileId -> index in files[] for quick updates from websocket events
  const fileIdIndexRef = useRef<Record<string, number>>({});

  // WebSocket integration
  const { subscribeToClaim, lastMessage } = useWebSocket();

  // Handle dropped or selected files
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
    // Handle rejected files (too large, wrong type, etc.)
    if (rejectedFiles.length > 0) {
      const errorMessages = rejectedFiles.map(({ file, errors }) => {
        if (file.size > maxFileSize) {
          return `${file.name} exceeds the maximum file size of ${maxFileSize / (1024 * 1024)}MB`;
        }
        const first = errors[0]?.message ?? 'could not be added';
        return `${file.name} ${first}`;
      });
      setErrors(prev => [...prev, ...errorMessages]);
      return;
    }

    // Check if adding these files would exceed the maximum
    if (files.length + acceptedFiles.length > maxFiles) {
      setErrors(prev => [...prev, `You can only upload a maximum of ${maxFiles} files at once`]);
      // Only add files up to the limit
      const remainingSlots = maxFiles - files.length;
      if (remainingSlots <= 0) return;
      acceptedFiles = acceptedFiles.slice(0, remainingSlots);
    }

    // Add status and progress to each file
    const filesWithStatus = acceptedFiles.map(file => ({
      file,
      status: 'pending' as FileStatus,
      progress: 0,
    }));

    setFiles(prev => [...prev, ...filesWithStatus]);
  }, [files, maxFileSize, maxFiles]);

  // Configure dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp'],
      'application/pdf': ['.pdf']
    },
    maxSize: maxFileSize,
    maxFiles: maxFiles
  });

  // Remove a file from the list
  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Clear all files
  const clearFiles = () => {
    setFiles([]);
    setErrors([]);
  };

  // Clear a specific error
  const clearError = (index: number) => {
    setErrors(prev => prev.filter((_, i) => i !== index));
  };

  // Group files into batches to stay under AWS limits
  const createFileBatches = (filesToUpload: FileWithStatus[]): FileWithStatus[][] => {
    const batches: FileWithStatus[][] = [];
    let currentBatch: FileWithStatus[] = [];
    let currentBatchSize = 0;

    filesToUpload.forEach(fileWithStatus => {
      // If adding this file would exceed the batch size limit, start a new batch
      if (currentBatchSize + fileWithStatus.file.size > MAX_BATCH_SIZE) {
        if (currentBatch.length > 0) {
          batches.push(currentBatch);
          currentBatch = [];
          currentBatchSize = 0;
        }
      }

      // If the file is larger than the max batch size, it gets its own batch
      if (fileWithStatus.file.size > MAX_BATCH_SIZE) {
        batches.push([fileWithStatus]);
      } else {
        currentBatch.push(fileWithStatus);
        currentBatchSize += fileWithStatus.file.size;
      }
    });

    // Add the last batch if it has files
    if (currentBatch.length > 0) {
      batches.push(currentBatch);
    }

    return batches;
  };

  // Upload a single batch via presigned S3 URLs
  interface PresignedFile {
    name: string;
    status: string;
    upload_url?: string;
    s3_key?: string;
    method?: string;
    content_type?: string | null;
    expires_in?: number;
    claim_id?: string;
    room_id?: string | null;
    timestamp?: string;
    file_id: string;
    batch_id: string;
    error?: string;
  }

  interface UploadUrlResponseBody {
    data?: {
      files?: PresignedFile[];
      batch_id?: string;
    };
    error_details?: string;
  }

  const uploadBatch = async (batch: FileWithStatus[]): Promise<PresignedFile[]> => {
    const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
    const uploadEndpoint = `${apiUrl}/claims/${claimId}/upload-url`;

    // Build request body expected by backend
    const requestBody = {
      files: batch.map(b => ({ name: b.file.name, content_type: b.file.type || undefined })),
      room_id: roomId ?? undefined
    };

    console.warn(`Requesting presigned URLs for ${batch.length} files -> ${uploadEndpoint}`);

    const resp = await fetch(uploadEndpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });

    if (!resp.ok) {
      let detail = 'Failed to request upload URLs';
      try {
        const body: UploadUrlResponseBody = await resp.json();
        if (body?.error_details) detail = body.error_details;
      } catch {}
      throw new Error(detail);
    }

    const body: UploadUrlResponseBody = await resp.json();
    const presigned = body?.data?.files ?? [];

    // Track batch for WS correlation
    const batchId = body?.data?.batch_id;
    if (batchId) {
      activeBatchIdsRef.current.add(batchId);
    }

    // Assign file IDs to local entries early for WS matching
    setFiles(prev => prev.map(f => {
      const match = presigned.find(p => p.name === f.file.name);
      if (match) {
        // keep current status (likely 'uploading')
        const idx = prev.indexOf(f);
        if (idx >= 0 && match.file_id) {
          fileIdIndexRef.current[match.file_id] = idx;
        }
        return { ...f, id: match.file_id };
      }
      return f;
    }));

    // Now perform uploads to S3
    const uploadResults = await Promise.allSettled(presigned.map(async (p) => {
      if (p.status !== 'ready' || !p.upload_url) {
        throw new Error(p.error || `Upload URL not ready for ${p.name}`);
      }
      const file = batch.find(b => b.file.name === p.name)?.file;
      if (!file) throw new Error(`File not found in batch for ${p.name}`);

      const putResp = await fetch(p.upload_url, {
        method: p.method || 'PUT',
        headers: {
          'Content-Type': p.content_type || 'application/octet-stream'
        },
        body: file
      });
      if (!putResp.ok) {
        throw new Error(`S3 upload failed (${putResp.status}) for ${p.name}`);
      }
      return p;
    }));

    const succeeded: PresignedFile[] = [];
    const failedMsgs: string[] = [];

    uploadResults.forEach((res, i) => {
      const p = presigned[i];
      if (res.status === 'fulfilled') {
        succeeded.push(p);
      } else {
        failedMsgs.push(`${p?.name || 'file'}: ${res.reason?.message || 'upload failed'}`);
      }
    });

    if (failedMsgs.length) {
      setErrors(prev => [...prev, ...failedMsgs.map(m => `Upload failed: ${m}`)]);
    }

    // Update UI statuses for succeeded uploads
    setFiles(prev => prev.map(f => {
      const ok = succeeded.find(p => p.name === f.file.name);
      if (ok && f.status === 'uploading') {
        return { ...f, status: 'uploaded', progress: 100, id: ok.file_id };
      }
      return f;
    }));

    return presigned;
  };

  // Handle file upload with chunking
  const uploadFiles = async () => {
    if (files.length === 0) return;
    if (!claimId) {
      setErrors(prev => [...prev, "No claim ID provided for upload"]);
      return;
    }

    setUploading(true);
    setErrors([]);

    // Create batches of files to upload
    const pendingFiles = files.filter(f => f.status === 'pending');
    const batches = createFileBatches(pendingFiles);
    
    // Update file statuses to uploading
    setFiles(prev => 
      prev.map(file => 
        file.status === 'pending' ? { ...file, status: 'uploading' } : file
      )
    );

    const uploadedFiles: UploadedFileRef[] = [];
    const failedBatches: { batch: FileWithStatus[], error: string }[] = [];

    // Upload each batch
    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i];
      try {
        const presigned = await uploadBatch(batch);
        console.warn(`Batch ${i+1}/${batches.length} presigned + upload complete`, presigned);

        // Build minimal uploaded refs for callback
        const queued = presigned.map(p => ({
          id: p.file_id,
          file_id: p.file_id,
          file_name: p.name,
          status: 'uploaded' as FileStatus
        }));
        uploadedFiles.push(...queued);
      } catch (error: unknown) {
        console.error(`Batch ${i+1}/${batches.length} upload error:`, error);
        const message = error instanceof Error ? error.message : 'Unknown upload error';
        failedBatches.push({ batch, error: message });
        
        // Update file statuses to failed
        setFiles(prev => 
          prev.map(file => {
            if (batch.includes(file)) {
              return { ...file, status: 'failed', error: message };
            }
            return file;
          })
        );
      }
    }

    // Handle failed batches
    if (failedBatches.length > 0) {
      const errorMessages = failedBatches.map(({ error }) => `Upload failed: ${error}`);
      setErrors(prev => [...prev, ...errorMessages]);
    }

    // Call the completion handler with the new files
    if (uploadedFiles.length > 0) {
      onUploadComplete(uploadedFiles);
    }

    setUploading(false);
  };

  // Subscribe to claim for websocket events
  useEffect(() => {
    if (claimId) {
      try { subscribeToClaim(claimId); } catch {}
    }
  }, [claimId, subscribeToClaim]);

  // React to websocket messages
  useEffect(() => {
    if (!lastMessage || !lastMessage.type) return;
    const t = String(lastMessage.type);
    // data is expected as object containing batchId/itemId and possibly success/fileName
    const data = (lastMessage.data ?? {}) as Record<string, unknown>;
    const batchId = (data['batchId'] as string | undefined) ?? (data['batch_id'] as string | undefined);
    if (!batchId || !activeBatchIdsRef.current.has(batchId)) return;

    const itemId = String((data['itemId'] as string | undefined) ?? '');
    const targetIdx = itemId && fileIdIndexRef.current[itemId] !== undefined
      ? fileIdIndexRef.current[itemId]
      : -1;

    const updateStatus = (status: FileStatus) => {
      if (targetIdx < 0) return;
      setFiles(prev => prev.map((f, idx) => idx === targetIdx ? { ...f, status } : f));
    };

    const success = (() => {
      const raw = data['success'];
      if (typeof raw === 'boolean') return raw;
      const status = data['status'];
      if (typeof status === 'string') {
        const s = status.toLowerCase();
        return s === 'success' || s === 'completed' || s === 'processed';
      }
      return false;
    })();

    if (t === 'file_processed') {
      updateStatus(success ? 'processed' : 'error');
    } else if (t === 'analysis_completed' || t === 'analysis_complete') {
      updateStatus(success ? 'analyzed' : 'error');
    } else if (t === 'file_uploaded' || t === 'file_analysis_queued' || t === 'analysis_started') {
      // Mark as uploaded/awaiting processing
      updateStatus('uploaded');
    } else if (t === 'batch_completed' || t === 'batch_complete') {
      // Stop tracking this batch
      activeBatchIdsRef.current.delete(batchId);
    }
  }, [lastMessage]);

  // Trigger file input click
  const openFileDialog = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Get status text and color for a file
  const getFileStatusInfo = (status: FileStatus) => {
    switch (status) {
      case 'pending':
        return { text: 'Pending', color: 'text-gray-500' };
      case 'uploading':
        return { text: 'Uploading...', color: 'text-blue-500' };
      case 'uploaded':
        return { text: 'Uploaded', color: 'text-green-500' };
      case 'processed':
        return { text: 'Processed', color: 'text-green-600' };
      case 'analyzed':
        return { text: 'Analyzed', color: 'text-green-700' };
      case 'failed':
        return { text: 'Failed', color: 'text-red-500' };
      case 'error':
        return { text: 'Error', color: 'text-red-600' };
      case 'skipped_analysis':
        return { text: 'Skipped Analysis', color: 'text-yellow-500' };
      default:
        return { text: 'Unknown', color: 'text-gray-500' };
    }
  };

  return (
    <div className="w-full">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        onClick={openFileDialog}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
        }`}
      >
        <input {...getInputProps()} ref={fileInputRef} />
        <ArrowUpTrayIcon className="h-10 w-10 mx-auto text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">
          {isDragActive
            ? 'Drop the files here...'
            : 'Drag & drop files here, or click to select files'}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Max {maxFiles} files, up to {maxFileSize / (1024 * 1024)}MB each
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-medium text-gray-700">Selected Files ({files.length})</h3>
            <button
              type="button"
              onClick={clearFiles}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Clear All
            </button>
          </div>
          
          {showPlaceholderCards ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {files.map((file, index) => (
                <UploadPlaceholderCard
                  key={index}
                  fileName={file.file.name}
                  progress={file.progress}
                  status={file.status}
                  className={file.status === 'pending' ? 'cursor-pointer' : ''}
                />
              ))}
            </div>
          ) : (
            <ul className="space-y-2 max-h-40 overflow-y-auto">
              {files.map((file, index) => {
                const { text, color } = getFileStatusInfo(file.status);
                return (
                  <li key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                    <div className="flex-1 flex items-center">
                      <span className="text-sm truncate max-w-xs">{file.file.name}</span>
                      <span className="text-xs text-gray-500 ml-2">
                        ({(file.file.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                    <div className={`text-xs ${color} mx-2`}>{text}</div>
                    {file.status === 'pending' && (
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          
          <button
            type="button"
            onClick={uploadFiles}
            disabled={uploading || files.every(f => f.status !== 'pending')}
            className="mt-4 w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload Files'}
          </button>
        </div>
      )}

      {/* Error messages */}
      {errors.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-red-700 mb-2">Errors</h3>
          <ul className="space-y-1 text-sm text-red-600">
            {errors.map((error, index) => (
              <li key={index} className="flex justify-between items-center">
                <span>{error}</span>
                <button
                  type="button"
                  onClick={() => clearError(index)}
                  className="text-red-400 hover:text-red-600"
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
