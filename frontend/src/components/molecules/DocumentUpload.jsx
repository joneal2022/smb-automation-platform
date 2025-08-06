import React, { useState, useCallback, useRef } from 'react';
import { 
  Card, Alert, Button, ProgressBar, Badge, Row, Col, 
  Form, Modal, ListGroup, Spinner 
} from 'react-bootstrap';
import { 
  Upload, FileText, Image, FileX, CheckCircle, 
  AlertCircle, X, Trash2, Eye, AlertTriangle 
} from 'lucide-react';

const DocumentUpload = ({ 
  onUploadComplete, 
  onUploadError,
  maxFiles = 10,
  maxFileSize = 50 * 1024 * 1024, // 50MB
  allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  documentType = null,
  batchMode = false
}) => {
  const [files, setFiles] = useState([]);
  const [isDragActive, setIsDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploading, setUploading] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  const [errors, setErrors] = useState([]);
  
  const fileInputRef = useRef(null);
  const dropRef = useRef(null);

  // File validation
  const validateFile = (file) => {
    const errors = [];
    
    // Check file size
    if (file.size > maxFileSize) {
      errors.push(`File size exceeds ${Math.round(maxFileSize / (1024 * 1024))}MB limit`);
    }
    
    // Check file type
    if (!allowedTypes.includes(file.type)) {
      errors.push('File type not supported');
    }
    
    // Check for duplicate
    const isDuplicate = files.some(existingFile => 
      existingFile.name === file.name && existingFile.size === file.size
    );
    if (isDuplicate) {
      errors.push('Duplicate file');
    }
    
    return errors;
  };

  // Get file icon based on type
  const getFileIcon = (file) => {
    if (!file.type) {
      return <FileText size={24} className="text-primary" />;
    }
    if (file.type.startsWith('image/')) {
      return <Image size={24} className="text-info" />;
    } else if (file.type === 'application/pdf') {
      return <FileText size={24} className="text-danger" />;
    } else {
      return <FileText size={24} className="text-primary" />;
    }
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Handle drag events
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragActive(true);
    }
  }, []);

  const handleDragOut = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  }, []);

  // Handle file selection
  const handleFiles = (newFiles) => {
    const validFiles = [];
    const fileErrors = [];

    newFiles.forEach((file) => {
      const validationErrors = validateFile(file);
      if (validationErrors.length === 0) {
        const fileWithId = {
          ...file,
          id: Math.random().toString(36).substr(2, 9),
          preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
          status: 'pending',
          uploadProgress: 0
        };
        validFiles.push(fileWithId);
      } else {
        fileErrors.push({
          fileName: file.name,
          errors: validationErrors
        });
      }
    });

    // Check total file limit
    if (files.length + validFiles.length > maxFiles) {
      fileErrors.push({
        fileName: 'Multiple files',
        errors: [`Cannot upload more than ${maxFiles} files at once`]
      });
      return;
    }

    setFiles(prev => [...prev, ...validFiles]);
    setErrors(fileErrors);

    // Clear errors after 5 seconds
    if (fileErrors.length > 0) {
      setTimeout(() => setErrors([]), 5000);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
    // Reset input
    e.target.value = '';
  };

  const removeFile = (fileId) => {
    setFiles(prev => {
      const updated = prev.filter(file => file.id !== fileId);
      // Clean up preview URLs
      const fileToRemove = prev.find(file => file.id === fileId);
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview);
      }
      return updated;
    });
  };

  const handlePreviewFile = (file) => {
    setPreviewFile(file);
    setShowPreviewModal(true);
  };

  // Upload files
  const uploadFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);
    const formData = new FormData();

    // Add document type if specified
    if (documentType) {
      formData.append('document_type', documentType);
    }

    // Add batch information if in batch mode
    if (batchMode) {
      formData.append('batch_mode', 'true');
      formData.append('batch_name', `Batch Upload - ${new Date().toLocaleString()}`);
    }

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        formData.append('files', file, file.name);

        // Update file status
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, status: 'uploading' } : f
        ));

        // Simulate upload progress (replace with actual upload logic)
        const simulateProgress = (fileId) => {
          let progress = 0;
          const interval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress >= 100) {
              progress = 100;
              clearInterval(interval);
              setFiles(prev => prev.map(f => 
                f.id === fileId ? { ...f, status: 'completed', uploadProgress: 100 } : f
              ));
            } else {
              setFiles(prev => prev.map(f => 
                f.id === fileId ? { ...f, uploadProgress: progress } : f
              ));
            }
          }, 200);
        };

        simulateProgress(file.id);
      }

      // Simulate API call delay
      setTimeout(() => {
        setUploading(false);
        if (onUploadComplete) {
          onUploadComplete(files);
        }
      }, 2000);

    } catch (error) {
      setUploading(false);
      if (onUploadError) {
        onUploadError(error);
      }
      
      // Mark files as failed
      setFiles(prev => prev.map(f => ({ ...f, status: 'error' })));
    }
  };

  const clearAll = () => {
    // Clean up preview URLs
    files.forEach(file => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview);
      }
    });
    setFiles([]);
    setErrors([]);
  };

  const getStatusBadge = (file) => {
    switch (file.status) {
      case 'pending':
        return <Badge bg="secondary">Pending</Badge>;
      case 'uploading':
        return <Badge bg="primary">Uploading</Badge>;
      case 'completed':
        return <Badge bg="success">Complete</Badge>;
      case 'error':
        return <Badge bg="danger">Error</Badge>;
      default:
        return <Badge bg="secondary">Unknown</Badge>;
    }
  };

  return (
    <div data-testid="document-upload-component">
      {/* Upload Zone */}
      <Card 
        className={`mb-3 ${isDragActive ? 'border-primary' : ''}`}
        ref={dropRef}
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <Card.Body 
          className={`text-center py-5 ${isDragActive ? 'bg-light border-primary' : ''}`}
          data-testid="document-upload-zone"
        >
          <div className="mb-3">
            <Upload 
              size={48} 
              className={`${isDragActive ? 'text-primary' : 'text-muted'}`} 
            />
          </div>
          <h5 className="mb-2">
            {isDragActive ? 'Drop files here' : 'Upload Documents'}
          </h5>
          <p className="text-muted mb-3">
            Drag and drop files here, or click to select files
          </p>
          <Button 
            variant="primary" 
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            data-testid="select-files-button"
          >
            Select Files
          </Button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInput}
            multiple
            accept={allowedTypes.join(',')}
            style={{ display: 'none' }}
            data-testid="file-input"
          />
          <div className="mt-3">
            <small className="text-muted">
              Supported formats: PDF, JPG, PNG, DOC, DOCX • Max size: {Math.round(maxFileSize / (1024 * 1024))}MB • Max files: {maxFiles}
            </small>
          </div>
        </Card.Body>
      </Card>

      {/* Error Messages */}
      {errors.length > 0 && (
        <Alert variant="danger" dismissible onClose={() => setErrors([])} data-testid="upload-errors">
          <AlertTriangle size={16} className="me-2" />
          <strong>Upload Errors:</strong>
          <ul className="mb-0 mt-2">
            {errors.map((error, index) => (
              <li key={index}>
                <strong>{error.fileName}:</strong> {error.errors.join(', ')}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {/* File List */}
      {files.length > 0 && (
        <Card data-testid="file-list-card">
          <Card.Header className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">Selected Files ({files.length})</h6>
            <div>
              <Button 
                variant="outline-danger" 
                size="sm" 
                onClick={clearAll}
                disabled={uploading}
                className="me-2"
                data-testid="clear-all-button"
              >
                <Trash2 size={16} className="me-1" />
                Clear All
              </Button>
              <Button 
                variant="success" 
                onClick={uploadFiles}
                disabled={uploading || files.length === 0}
                data-testid="upload-files-button"
              >
                {uploading ? (
                  <>
                    <Spinner size="sm" animation="border" className="me-2" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload size={16} className="me-1" />
                    Upload Files
                  </>
                )}
              </Button>
            </div>
          </Card.Header>
          <ListGroup variant="flush">
            {files.map((file) => (
              <ListGroup.Item key={file.id} data-testid={`file-item-${file.id}`}>
                <Row className="align-items-center">
                  <Col xs="auto">
                    {getFileIcon(file)}
                  </Col>
                  <Col>
                    <div className="fw-medium">{file.name}</div>
                    <small className="text-muted">
                      {formatFileSize(file.size)} • {file.type}
                    </small>
                    {file.status === 'uploading' && (
                      <ProgressBar 
                        now={file.uploadProgress} 
                        size="sm" 
                        className="mt-1"
                        data-testid={`progress-${file.id}`}
                      />
                    )}
                  </Col>
                  <Col xs="auto">
                    {getStatusBadge(file)}
                  </Col>
                  <Col xs="auto">
                    <div className="d-flex gap-1">
                      {file.preview && (
                        <Button
                          variant="outline-primary"
                          size="sm"
                          onClick={() => handlePreviewFile(file)}
                          data-testid={`preview-${file.id}`}
                        >
                          <Eye size={14} />
                        </Button>
                      )}
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() => removeFile(file.id)}
                        disabled={uploading}
                        data-testid={`remove-${file.id}`}
                      >
                        <X size={14} />
                      </Button>
                    </div>
                  </Col>
                </Row>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Card>
      )}

      {/* Preview Modal */}
      <Modal 
        show={showPreviewModal} 
        onHide={() => setShowPreviewModal(false)}
        size="lg"
        centered
        data-testid="preview-modal"
      >
        <Modal.Header closeButton>
          <Modal.Title>Preview: {previewFile?.name}</Modal.Title>
        </Modal.Header>
        <Modal.Body className="text-center">
          {previewFile?.preview ? (
            <img 
              src={previewFile.preview} 
              alt="Preview" 
              className="img-fluid"
              style={{ maxHeight: '500px' }}
            />
          ) : (
            <div className="py-5">
              <FileText size={64} className="text-muted mb-3" />
              <p className="text-muted">Preview not available for this file type</p>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowPreviewModal(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default DocumentUpload;