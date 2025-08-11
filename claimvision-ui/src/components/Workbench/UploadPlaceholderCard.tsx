import React from 'react';
import Image from 'next/image';

interface UploadPlaceholderCardProps {
  fileName: string;
  progress: number;
  status: 'pending' | 'uploading' | 'uploaded' | 'processed' | 'failed' | 'analyzed' | 'skipped_analysis' | 'error';
  className?: string;
}

const UploadPlaceholderCard: React.FC<UploadPlaceholderCardProps> = ({
  fileName,
  progress,
  status,
  className = '',
}) => {
  // Get status text and color
  const getStatusInfo = () => {
    switch (status) {
      case 'pending':
        return { text: 'Pending', color: 'text-gray-500', bgColor: 'bg-gray-200' };
      case 'uploading':
        return { text: `Uploading ${progress}%`, color: 'text-blue-500', bgColor: 'bg-blue-200' };
      case 'uploaded':
        return { text: 'Processing...', color: 'text-green-500', bgColor: 'bg-green-200' };
      case 'processed':
        return { text: 'Processed', color: 'text-green-600', bgColor: 'bg-green-200' };
      case 'analyzed':
        return { text: 'Analyzed', color: 'text-green-700', bgColor: 'bg-green-200' };
      case 'failed':
        return { text: 'Failed', color: 'text-red-500', bgColor: 'bg-red-200' };
      case 'error':
        return { text: 'Error', color: 'text-red-600', bgColor: 'bg-red-200' };
      case 'skipped_analysis':
        return { text: 'Skipped Analysis', color: 'text-yellow-500', bgColor: 'bg-yellow-200' };
      default:
        return { text: 'Unknown', color: 'text-gray-500', bgColor: 'bg-gray-200' };
    }
  };

  const { text, color, bgColor } = getStatusInfo();

  return (
    <div
      className={`
        relative bg-white rounded-lg shadow-md overflow-hidden transition-all duration-300 ease-in-out
        border border-gray-200 hover:shadow-lg
        ${className}
      `}
    >
      {/* Image */}
      <div className="aspect-square overflow-hidden relative">
        <Image
          src="/placeholder-upload.svg"
          alt="Uploading file"
          fill
          sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 25vw"
          className="object-cover"
          unoptimized
        />
        
        {/* Progress overlay */}
        {status === 'uploading' && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200">
            <div 
              className="h-full bg-blue-500 transition-all duration-300 ease-in-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-3">
        {/* Title */}
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-medium truncate text-gray-900">
            {fileName}
          </h3>
        </div>

        {/* Status badge */}
        <div className="flex items-center">
          <span className={`inline-block px-2 py-1 text-xs rounded-full ${color} ${bgColor}`}>
            {text}
          </span>
        </div>
      </div>
    </div>
  );
};

export default UploadPlaceholderCard;
