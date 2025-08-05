import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Container, Row, Col, Card, Tab, Tabs, Alert, Button, 
  Table, Badge, Form, Modal, Spinner, ProgressBar 
} from 'react-bootstrap';
import { 
  Upload, FileText, Search, Filter, Download, Eye, 
  Clock, CheckCircle, AlertCircle, RefreshCw, Settings, Edit, Layers 
} from 'lucide-react';
import { useAuth } from '../../services/auth/AuthContext';
import DocumentUpload from '../../components/molecules/DocumentUpload';
import BatchProcessingInterface from '../../components/molecules/BatchProcessingInterface';

const DocumentProcessingPage = () => {
  const { user, canAccessFeature } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('upload');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingStats, setProcessingStats] = useState({
    total: 0,
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0
  });
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Sample document data (replace with API calls)
  useEffect(() => {
    // Simulate loading documents
    setLoading(true);
    setTimeout(() => {
      setDocuments([
        {
          id: '1',
          filename: 'invoice_001.pdf',
          type: 'Invoice',
          status: 'completed',
          uploadedAt: '2025-08-01T10:30:00Z',
          processedAt: '2025-08-01T10:31:15Z',
          confidence: 0.95,
          size: '2.4 MB',
          extractedFields: 12
        },
        {
          id: '2',
          filename: 'contract_draft.docx',
          type: 'Contract',
          status: 'processing',
          uploadedAt: '2025-08-01T11:15:00Z',
          confidence: null,
          size: '1.8 MB',
          extractedFields: 0
        },
        {
          id: '3',
          filename: 'receipt_scan.jpg',
          type: 'Receipt',
          status: 'review_required',
          uploadedAt: '2025-08-01T09:45:00Z',
          processedAt: '2025-08-01T09:46:30Z',
          confidence: 0.72,
          size: '3.1 MB',
          extractedFields: 8
        }
      ]);

      setProcessingStats({
        total: 3,
        pending: 0,
        processing: 1,
        completed: 1,
        failed: 0,
        review_required: 1
      });

      setLoading(false);
    }, 1000);
  }, []);

  const handleUploadComplete = (files) => {
    setUploadSuccess(true);
    setActiveTab('processing');
    // Simulate adding new documents to the list
    const newDocuments = files.map((file, index) => ({
      id: `new_${Date.now()}_${index}`,
      filename: file.name,
      type: 'Auto-detected',
      status: 'processing',
      uploadedAt: new Date().toISOString(),
      confidence: null,
      size: (file.size / (1024 * 1024)).toFixed(1) + ' MB',
      extractedFields: 0
    }));
    setDocuments(prev => [...newDocuments, ...prev]);
    
    // Clear success message after 5 seconds
    setTimeout(() => setUploadSuccess(false), 5000);
  };

  const handleUploadError = (error) => {
    console.error('Upload error:', error);
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      'uploaded': { variant: 'secondary', text: 'Uploaded' },
      'processing': { variant: 'primary', text: 'Processing' },
      'ocr_complete': { variant: 'info', text: 'OCR Complete' },
      'extraction_complete': { variant: 'info', text: 'Extraction Complete' },
      'review_required': { variant: 'warning', text: 'Review Required' },
      'completed': { variant: 'success', text: 'Completed' },
      'approved': { variant: 'success', text: 'Approved' },
      'rejected': { variant: 'danger', text: 'Rejected' },
      'error': { variant: 'danger', text: 'Error' }
    };

    const config = statusConfig[status] || { variant: 'secondary', text: status };
    return <Badge bg={config.variant}>{config.text}</Badge>;
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'processing':
        return <Clock size={16} className="text-primary" />;
      case 'completed':
      case 'approved':
        return <CheckCircle size={16} className="text-success" />;
      case 'error':
      case 'rejected':
        return <AlertCircle size={16} className="text-danger" />;
      case 'review_required':
        return <AlertCircle size={16} className="text-warning" />;
      default:
        return <FileText size={16} className="text-muted" />;
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const retryProcessing = (documentId) => {
    // Simulate retry
    setDocuments(prev => prev.map(doc => 
      doc.id === documentId ? { ...doc, status: 'processing' } : doc
    ));
  };

  const downloadDocument = (documentId) => {
    // Simulate download
    console.log('Downloading document:', documentId);
  };

  const viewDocument = (documentId) => {
    // Simulate view
    console.log('Viewing document:', documentId);
  };

  const reviewDocument = (documentId) => {
    navigate(`/documents/review/${documentId}`);
  };

  return (
    <div className="min-vh-100 bg-light" data-testid="document-processing-page">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <Container>
          <Row className="align-items-center py-3">
            <Col>
              <div className="d-flex align-items-center">
                <FileText size={24} className="text-primary me-2" />
                <h4 className="mb-0 text-dark">Document Processing</h4>
              </div>
            </Col>
            <Col xs="auto">
              <Button 
                variant="outline-primary" 
                size="sm" 
                onClick={() => setShowSettingsModal(true)}
                data-testid="processing-settings-button"
              >
                <Settings size={16} className="me-1" />
                Settings
              </Button>
            </Col>
          </Row>
        </Container>
      </div>

      <Container className="py-4">
        {/* Success Message */}
        {uploadSuccess && (
          <Alert variant="success" dismissible onClose={() => setUploadSuccess(false)} data-testid="upload-success-alert">
            <CheckCircle size={16} className="me-2" />
            Files uploaded successfully! Processing has begun.
          </Alert>
        )}

        {/* Processing Stats */}
        <Row className="mb-4">
          <Col md={2}>
            <Card className="text-center border-primary" data-testid="stats-total">
              <Card.Body>
                <h3 className="text-primary mb-1">{processingStats.total}</h3>
                <small className="text-muted">Total Documents</small>
              </Card.Body>
            </Card>
          </Col>
          <Col md={2}>
            <Card className="text-center border-info" data-testid="stats-processing">
              <Card.Body>
                <h3 className="text-info mb-1">{processingStats.processing}</h3>
                <small className="text-muted">Processing</small>
              </Card.Body>
            </Card>
          </Col>
          <Col md={2}>
            <Card className="text-center border-success" data-testid="stats-completed">
              <Card.Body>
                <h3 className="text-success mb-1">{processingStats.completed}</h3>
                <small className="text-muted">Completed</small>
              </Card.Body>
            </Card>
          </Col>
          <Col md={2}>
            <Card className="text-center border-warning" data-testid="stats-review">
              <Card.Body>
                <h3 className="text-warning mb-1">{processingStats.review_required || 0}</h3>
                <small className="text-muted">Need Review</small>
              </Card.Body>
            </Card>
          </Col>
          <Col md={2}>
            <Card className="text-center border-danger" data-testid="stats-failed">
              <Card.Body>
                <h3 className="text-danger mb-1">{processingStats.failed}</h3>
                <small className="text-muted">Failed</small>
              </Card.Body>
            </Card>
          </Col>
          <Col md={2}>
            <Card className="text-center" data-testid="stats-accuracy">
              <Card.Body>
                <h3 className="text-dark mb-1">94%</h3>
                <small className="text-muted">Accuracy</small>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Main Content Tabs */}
        <Card data-testid="document-processing-tabs">
          <Tabs
            activeKey={activeTab}
            onSelect={(k) => setActiveTab(k)}
            className="px-3 pt-3"
            data-testid="processing-tabs"
          >
            {/* Upload Tab */}
            <Tab eventKey="upload" title={
              <span data-testid="upload-tab">
                <Upload size={16} className="me-1" />
                Upload Documents
              </span>
            }>
              <Card.Body>
                <Row>
                  <Col lg={8}>
                    <DocumentUpload
                      onUploadComplete={handleUploadComplete}
                      onUploadError={handleUploadError}
                      maxFiles={10}
                      batchMode={true}
                    />
                  </Col>
                  <Col lg={4}>
                    <Card className="bg-light border-0" data-testid="upload-tips">
                      <Card.Body>
                        <h6 className="text-dark mb-3">
                          <FileText size={16} className="me-2" />
                          Upload Tips
                        </h6>
                        <ul className="small text-muted mb-0">
                          <li>Ensure documents are clear and well-lit</li>
                          <li>Avoid shadows or reflections on documents</li>
                          <li>PDF files provide best OCR accuracy</li>
                          <li>Use batch upload for multiple similar documents</li>
                          <li>Check file size limits before uploading</li>
                        </ul>
                      </Card.Body>
                    </Card>

                    <Card className="mt-3 bg-primary text-white" data-testid="processing-info">
                      <Card.Body>
                        <h6 className="mb-3">
                          <CheckCircle size={16} className="me-2" />
                          What Happens Next?
                        </h6>
                        <ol className="small mb-0">
                          <li>Files are validated and scanned</li>
                          <li>OCR extracts text from images/PDFs</li>
                          <li>AI identifies document type</li>
                          <li>Key data fields are extracted</li>
                          <li>Results are available for review</li>
                        </ol>
                      </Card.Body>
                    </Card>
                  </Col>
                </Row>
              </Card.Body>
            </Tab>

            {/* Processing Queue Tab */}
            <Tab eventKey="processing" title={
              <span data-testid="processing-tab">
                <Clock size={16} className="me-1" />
                Processing Queue
              </span>
            }>
              <Card.Body>
                <Row className="mb-3">
                  <Col md={6}>
                    <Form.Control
                      type="text"
                      placeholder="Search documents..."
                      data-testid="document-search"
                    />
                  </Col>
                  <Col md={3}>
                    <Form.Select data-testid="status-filter">
                      <option value="">All Status</option>
                      <option value="processing">Processing</option>
                      <option value="completed">Completed</option>
                      <option value="review_required">Review Required</option>
                      <option value="error">Error</option>
                    </Form.Select>
                  </Col>
                  <Col md={3}>
                    <Form.Select data-testid="type-filter">
                      <option value="">All Types</option>
                      <option value="invoice">Invoice</option>
                      <option value="contract">Contract</option>
                      <option value="receipt">Receipt</option>
                      <option value="form">Form</option>
                    </Form.Select>
                  </Col>
                </Row>

                {loading ? (
                  <div className="text-center py-4">
                    <Spinner animation="border" variant="primary" />
                    <p className="mt-2 text-muted">Loading documents...</p>
                  </div>
                ) : (
                  <Table responsive hover data-testid="documents-table">
                    <thead>
                      <tr>
                        <th>Document</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Uploaded</th>
                        <th>Confidence</th>
                        <th>Fields</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc) => (
                        <tr key={doc.id} data-testid={`document-row-${doc.id}`}>
                          <td>
                            <div className="d-flex align-items-center">
                              {getStatusIcon(doc.status)}
                              <div className="ms-2">
                                <div className="fw-medium">{doc.filename}</div>
                                <small className="text-muted">{doc.size}</small>
                              </div>
                            </div>
                          </td>
                          <td>
                            <Badge bg="light" text="dark">{doc.type}</Badge>
                          </td>
                          <td>{getStatusBadge(doc.status)}</td>
                          <td>
                            <small>{formatDate(doc.uploadedAt)}</small>
                          </td>
                          <td>
                            {doc.confidence ? (
                              <div>
                                <ProgressBar 
                                  now={doc.confidence * 100} 
                                  size="sm"
                                  variant={doc.confidence > 0.8 ? 'success' : doc.confidence > 0.6 ? 'warning' : 'danger'}
                                />
                                <small>{Math.round(doc.confidence * 100)}%</small>
                              </div>
                            ) : (
                              <small className="text-muted">N/A</small>
                            )}
                          </td>
                          <td>
                            <Badge bg="info">{doc.extractedFields}</Badge>
                          </td>
                          <td>
                            <div className="d-flex gap-1">
                              <Button
                                variant="outline-primary"
                                size="sm"
                                onClick={() => viewDocument(doc.id)}
                                data-testid={`view-${doc.id}`}
                                title="View Document"
                              >
                                <Eye size={14} />
                              </Button>
                              {doc.status === 'review_required' && (
                                <Button
                                  variant="outline-warning"
                                  size="sm"
                                  onClick={() => reviewDocument(doc.id)}
                                  data-testid={`review-${doc.id}`}
                                  title="Review & Correct"
                                >
                                  <Edit size={14} />
                                </Button>
                              )}
                              <Button
                                variant="outline-secondary"
                                size="sm"
                                onClick={() => downloadDocument(doc.id)}
                                data-testid={`download-${doc.id}`}
                                title="Download"
                              >
                                <Download size={14} />
                              </Button>
                              {doc.status === 'error' && (
                                <Button
                                  variant="outline-warning"
                                  size="sm"
                                  onClick={() => retryProcessing(doc.id)}
                                  data-testid={`retry-${doc.id}`}
                                  title="Retry Processing"
                                >
                                  <RefreshCw size={14} />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </Card.Body>
            </Tab>

            {/* Review Tab */}
            <Tab eventKey="review" title={
              <span data-testid="review-tab">
                <AlertCircle size={16} className="me-1" />
                Review Required {processingStats.review_required > 0 && <Badge bg="warning">{processingStats.review_required}</Badge>}
              </span>
            }>
              <Card.Body>
                <Alert variant="info" data-testid="review-info">
                  <AlertCircle size={16} className="me-2" />
                  Documents with confidence scores below 80% require manual review to ensure accuracy.
                </Alert>
                
                {documents.filter(doc => doc.status === 'review_required').length === 0 ? (
                  <div className="text-center py-4">
                    <CheckCircle size={48} className="text-success mb-3" />
                    <h5>All Clear!</h5>
                    <p className="text-muted">
                      No documents currently require manual review.
                    </p>
                  </div>
                ) : (
                  <Table responsive hover data-testid="review-documents-table">
                    <thead>
                      <tr>
                        <th>Document</th>
                        <th>Type</th>
                        <th>Confidence</th>
                        <th>Extracted Fields</th>
                        <th>Uploaded</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.filter(doc => doc.status === 'review_required').map((doc) => (
                        <tr key={doc.id} data-testid={`review-row-${doc.id}`}>
                          <td>
                            <div className="d-flex align-items-center">
                              <AlertCircle size={16} className="text-warning me-2" />
                              <div>
                                <div className="fw-medium">{doc.filename}</div>
                                <small className="text-muted">{doc.size}</small>
                              </div>
                            </div>
                          </td>
                          <td>
                            <Badge bg="light" text="dark">{doc.type}</Badge>
                          </td>
                          <td>
                            <div>
                              <ProgressBar 
                                now={doc.confidence * 100} 
                                size="sm"
                                variant="warning"
                              />
                              <small className="text-warning fw-medium">{Math.round(doc.confidence * 100)}% (Low)</small>
                            </div>
                          </td>
                          <td>
                            <Badge bg="info">{doc.extractedFields} fields</Badge>
                          </td>
                          <td>
                            <small>{formatDate(doc.uploadedAt)}</small>
                          </td>
                          <td>
                            <Button
                              variant="warning"
                              size="sm"
                              onClick={() => reviewDocument(doc.id)}
                              data-testid={`start-review-${doc.id}`}
                            >
                              <Edit size={14} className="me-1" />
                              Start Review
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </Card.Body>
            </Tab>

            {/* Batch Processing Tab */}
            <Tab eventKey="batch" title={
              <span data-testid="batch-tab">
                <Layers size={16} className="me-1" />
                Batch Processing
              </span>
            }>
              <Card.Body>
                <BatchProcessingInterface />
              </Card.Body>
            </Tab>
          </Tabs>
        </Card>
      </Container>

      {/* Settings Modal */}
      <Modal show={showSettingsModal} onHide={() => setShowSettingsModal(false)} data-testid="settings-modal">
        <Modal.Header closeButton>
          <Modal.Title>Processing Settings</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Auto-approval Threshold</Form.Label>
              <Form.Range min={0} max={100} defaultValue={80} />
              <Form.Text className="text-muted">
                Documents with confidence above this threshold will be auto-approved.
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Default Document Type</Form.Label>
              <Form.Select>
                <option>Auto-detect</option>
                <option>Invoice</option>
                <option>Contract</option>
                <option>Receipt</option>
                <option>Form</option>
              </Form.Select>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Check 
                type="checkbox" 
                label="Enable OCR for image files"
                defaultChecked
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Check 
                type="checkbox" 
                label="Automatically extract key fields"
                defaultChecked
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowSettingsModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => setShowSettingsModal(false)}>
            Save Settings
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default DocumentProcessingPage;