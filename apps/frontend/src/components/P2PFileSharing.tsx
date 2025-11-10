/**
 * P2P File Sharing UI
 *
 * Allows users to:
 * - Share files with specific channels
 * - View shared files across the mesh
 * - Download files from peers
 * - Track upload/download progress
 */

import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';
import {
  Upload,
  Download,
  File,
  FileText,
  Image,
  Video,
  Music,
  Archive,
  X,
  Check,
  Loader2,
  Trash2,
  Search
} from 'lucide-react';
import {
  shareFile,
  downloadFile,
  getSharedFiles,
  getChannels,
  type Channel
} from '../lib/p2pApi';

interface P2PFileSharingProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SharedFile {
  id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  shared_by: string;
  shared_at: string;
  channel_id: string;
  channel_name?: string;
}

interface UploadProgress {
  fileName: string;
  progress: number;
  channelId: string;
}

export function P2PFileSharing({ isOpen, onClose }: P2PFileSharingProps) {
  const [sharedFiles, setSharedFiles] = useState<SharedFile[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<Record<string, number>>({});
  const [dragActive, setDragActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load shared files and channels on mount
  useEffect(() => {
    if (isOpen) {
      loadData();
      // Refresh every 10 seconds
      const interval = setInterval(loadSharedFiles, 10000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const loadData = async () => {
    await Promise.all([loadSharedFiles(), loadChannels()]);
  };

  const loadSharedFiles = async () => {
    try {
      const files = await getSharedFiles();
      setSharedFiles(files);
    } catch (error) {
      console.error('Failed to load shared files:', error);
    }
  };

  const loadChannels = async () => {
    try {
      const channelList = await getChannels();
      setChannels(channelList);
      if (channelList.length > 0 && !selectedChannel) {
        setSelectedChannel(channelList[0].id);
      }
    } catch (error) {
      console.error('Failed to load channels:', error);
    }
  };

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (!selectedChannel) {
      toast.error('Please select a channel first');
      return;
    }

    const file = files[0];
    handleFileUpload(file);
  };

  const handleFileUpload = async (file: File) => {
    if (file.size > 100 * 1024 * 1024) { // 100MB limit
      toast.error('File size must be less than 100MB');
      return;
    }

    setUploadProgress({
      fileName: file.name,
      progress: 0,
      channelId: selectedChannel
    });

    try {
      await shareFile(selectedChannel, file, (progress) => {
        setUploadProgress(prev => prev ? { ...prev, progress } : null);
      });

      toast.success(`${file.name} shared successfully`);
      setUploadProgress(null);
      loadSharedFiles();
    } catch (error: any) {
      console.error('Failed to share file:', error);
      toast.error(error.response?.data?.message || 'Failed to share file');
      setUploadProgress(null);
    }
  };

  const handleFileDownload = async (file: SharedFile) => {
    setDownloadProgress(prev => ({ ...prev, [file.id]: 0 }));

    try {
      const blob = await downloadFile(file.id, (progress) => {
        setDownloadProgress(prev => ({ ...prev, [file.id]: progress }));
      });

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.file_name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`Downloaded ${file.file_name}`);
      setDownloadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[file.id];
        return newProgress;
      });
    } catch (error) {
      console.error('Failed to download file:', error);
      toast.error('Failed to download file');
      setDownloadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[file.id];
        return newProgress;
      });
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files);
    }
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return <Image className="w-5 h-5" />;
    if (mimeType.startsWith('video/')) return <Video className="w-5 h-5" />;
    if (mimeType.startsWith('audio/')) return <Music className="w-5 h-5" />;
    if (mimeType.includes('zip') || mimeType.includes('tar') || mimeType.includes('rar')) {
      return <Archive className="w-5 h-5" />;
    }
    if (mimeType.includes('text') || mimeType.includes('json') || mimeType.includes('xml')) {
      return <FileText className="w-5 h-5" />;
    }
    return <File className="w-5 h-5" />;
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const filteredFiles = sharedFiles.filter(file =>
    file.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    file.shared_by.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg w-full max-w-4xl shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Upload className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              P2P File Sharing
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
          >
            <X size={20} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Upload Section */}
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              Share a File
            </h3>

            {/* Channel Selector */}
            <div className="flex gap-3">
              <select
                value={selectedChannel}
                onChange={(e) => setSelectedChannel(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select channel...</option>
                {channels.map((channel) => (
                  <option key={channel.id} value={channel.id}>
                    #{channel.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Drag & Drop Upload Area */}
            <div
              className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                onChange={(e) => handleFileSelect(e.target.files)}
                className="hidden"
              />

              {uploadProgress ? (
                <div className="space-y-3">
                  <Loader2 className="w-12 h-12 mx-auto text-blue-600 dark:text-blue-400 animate-spin" />
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Uploading {uploadProgress.fileName}
                    </p>
                    <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {uploadProgress.progress}%
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    Drag and drop a file here, or click to browse
                  </p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={!selectedChannel}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                  >
                    Choose File
                  </button>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Max file size: 100MB
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Shared Files Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                Shared Files ({filteredFiles.length})
              </h3>
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search files..."
                  className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {filteredFiles.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <File className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No files shared yet</p>
                <p className="text-xs mt-1">
                  Share files with your team using the upload area above
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredFiles.map((file) => {
                  const isDownloading = file.id in downloadProgress;
                  const progress = downloadProgress[file.id] || 0;

                  return (
                    <div
                      key={file.id}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="text-gray-600 dark:text-gray-400">
                          {getFileIcon(file.mime_type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                            {file.file_name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {formatFileSize(file.file_size)} • Shared by {file.shared_by} • {formatDate(file.shared_at)}
                          </div>
                          {file.channel_name && (
                            <div className="text-xs text-blue-600 dark:text-blue-400">
                              #{file.channel_name}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Download Button */}
                      <div className="ml-3">
                        {isDownloading ? (
                          <div className="flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                            <span className="text-xs text-gray-600 dark:text-gray-400">
                              {progress}%
                            </span>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleFileDownload(file)}
                            className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                            title="Download"
                          >
                            <Download className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors font-medium text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
