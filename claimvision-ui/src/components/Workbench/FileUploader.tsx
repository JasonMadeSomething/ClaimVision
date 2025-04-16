"use client";

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { ArrowUpTrayIcon, XMarkIcon } from '@heroicons/react/24/outline';
import UploadPlaceholderCard from './UploadPlaceholderCard';

interface FileUploaderProps {
  claimId: string;
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
  const [processingFiles, setProcessingFiles] = useState<any[]>([]);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Handle dropped or selected files
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files (too large, wrong type, etc.)
    if (rejectedFiles.length > 0) {
      const errorMessages = rejectedFiles.map(rejection => {
        if (rejection.file.size > maxFileSize) {
          return `${rejection.file.name} exceeds the maximum file size of ${maxFileSize / (1024 * 1024)}MB`;
        }
        return `${rejection.file.name} could not be added`;
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

  // Upload a single batch of files
  const uploadBatch = async (batch: FileWithStatus[]): Promise<any> => {
    const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
    const uploadEndpoint = `${apiUrl}/claims/${claimId}/files/upload`;
    
    // Instead of using FormData for files, we'll create a JSON structure with base64-encoded files
    // This ensures compatibility with the backend's expected format
    const filesData = await Promise.all(batch.map(async (fileWithStatus) => {
      // Convert the file to base64 using the FileReader API
      return {
        file_name: fileWithStatus.file.name,
        file_data: await readFileAsBase64(fileWithStatus.file)
      };
    }));
    
    // Create the request body
    const requestBody = {
      files: filesData,
      room_id: roomId
    };
    
    console.log(`Uploading ${batch.length} files to ${uploadEndpoint}`);
    console.log(`File names: ${filesData.map(f => f.file_name).join(', ')}`);
    
    // Upload the files as JSON instead of FormData
    const response = await fetch(uploadEndpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error_details || 'Failed to upload files');
    }
    
    return await response.json();
  };
  
  // Helper function to read a file as base64
  const readFileAsBase64 = (file: File): Promise<string> => {
    if (!(file instanceof Blob)) {
      throw new Error('Invalid file type');
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        // Get the base64 string (remove the data URL prefix)
        const result = reader.result as string;
        const base64String = result.split(',')[1];
        resolve(base64String);
      };
      reader.onerror = () => reject(reader.error);
      
      // Read the file as a data URL
      reader.readAsDataURL(file);
    });
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

    const uploadedFiles: any[] = [];
    const failedBatches: { batch: FileWithStatus[], error: string }[] = [];

    // Upload each batch
    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i];
      try {
        const result = await uploadBatch(batch);
        console.log(`Batch ${i+1}/${batches.length} upload successful:`, result);
        
        if (result.data && Array.isArray(result.data.files_queued)) {
          uploadedFiles.push(...result.data.files_queued);
          
          // Update file statuses to uploaded
          setFiles(prev => 
            prev.map(file => {
              const matchedFile = result.data.files_queued.find((f: any) => 
                f.file_name === file.file.name
              );
              if (matchedFile && file.status === 'uploading') {
                return { 
                  ...file, 
                  status: 'uploaded',
                  id: matchedFile.file_id || matchedFile.id,
                  progress: 100 
                };
              }
              return file;
            })
          );
        }
      } catch (error: any) {
        console.error(`Batch ${i+1}/${batches.length} upload error:`, error);
        failedBatches.push({ batch, error: error.message });
        
        // Update file statuses to failed
        setFiles(prev => 
          prev.map(file => {
            if (batch.includes(file)) {
              return { ...file, status: 'failed', error: error.message };
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
      setProcessingFiles(uploadedFiles);
      
      // Start polling for file status
      startPollingFileStatus();
    }

    setUploading(false);
  };

  // Poll for file status updates
  const startPollingFileStatus = useCallback(() => {
    // Clear any existing polling interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    // Set up a new polling interval
    const interval = setInterval(async () => {
      if (processingFiles.length === 0) {
        clearInterval(interval);
        setPollingInterval(null);
        return;
      }

      try {
        await checkFileStatus();
      } catch (error) {
        console.error('Error checking file status:', error);
      }
    }, 5000); // Poll every 5 seconds

    setPollingInterval(interval);

    // Cleanup on component unmount
    return () => {
      clearInterval(interval);
    };
  }, [processingFiles, authToken]);

  // Check the status of uploaded files
  const checkFileStatus = async () => {
    if (processingFiles.length === 0) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
    const fileIds = processingFiles.map(file => file.file_id || file.id).join(',');
    const statusEndpoint = `${apiUrl}/files?ids=${fileIds}`;

    try {
      const response = await fetch(statusEndpoint, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch file status');
      }

      const result = await response.json();
      if (result.data && Array.isArray(result.data.files)) {
        const updatedFiles = result.data.files;
        
        // Update file statuses
        setFiles(prev => 
          prev.map(file => {
            const matchedFile = updatedFiles.find((f: any) => 
              f.id === file.id
            );
            if (matchedFile) {
              return { 
                ...file, 
                status: matchedFile.status as FileStatus
              };
            }
            return file;
          })
        );

        // Remove processed files from the polling list
        setProcessingFiles(prev => 
          prev.filter(file => {
            const matchedFile = updatedFiles.find((f: any) => 
              (f.file_id || f.id) === (file.file_id || file.id)
            );
            return !matchedFile || 
                  (matchedFile.status !== 'processed' && 
                   matchedFile.status !== 'analyzed' && 
                   matchedFile.status !== 'error');
          })
        );
      }
    } catch (error) {
      console.error('Error checking file status:', error);
    }
  };

  // Cleanup polling on component unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

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
