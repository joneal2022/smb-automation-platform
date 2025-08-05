import React, { useState, useEffect } from 'react';
import { 
    Container, Row, Col, Card, Badge, Button, Alert, Form, 
    Modal, Spinner, Table, InputGroup, ButtonGroup 
} from 'react-bootstrap';
import { 
    CheckCircle, XCircle, Clock, Eye, Edit3, Save, 
    X, AlertTriangle, FileText, Zap 
} from 'lucide-react';

const DocumentReviewInterface = ({ documentId, onReviewComplete }) => {
    const [document, setDocument] = useState(null);
    const [extractions, setExtractions] = useState([]);
    const [processingLogs, setProcessingLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [editingField, setEditingField] = useState(null);
    const [editValues, setEditValues] = useState({});
    const [showOcrText, setShowOcrText] = useState(false);
    const [verifyingFields, setVerifyingFields] = useState(new Set());

    useEffect(() => {
        if (documentId) {
            loadDocumentDetails();
        }
    }, [documentId]);

    const loadDocumentDetails = async () => {
        try {
            setLoading(true);
            setError(null);

            // Load document details
            const docResponse = await fetch(`/api/documents/${documentId}/`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (!docResponse.ok) {
                throw new Error('Failed to load document details');
            }

            const docData = await docResponse.json();
            setDocument(docData);

            // Load extractions
            const extractionsResponse = await fetch(`/api/documents/${documentId}/extractions/`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (!extractionsResponse.ok) {
                throw new Error('Failed to load extractions');
            }

            const extractionsData = await extractionsResponse.json();
            setExtractions(extractionsData);

            // Load processing logs
            const logsResponse = await fetch(`/api/documents/${documentId}/processing_logs/`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (!logsResponse.ok) {
                throw new Error('Failed to load processing logs');
            }

            const logsData = await logsResponse.json();
            setProcessingLogs(logsData);

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleEditField = (extraction) => {
        setEditingField(extraction.id);
        setEditValues({
            corrected_value: extraction.corrected_value || extraction.field_value,
            correction_reason: extraction.correction_reason || ''
        });
    };

    const handleSaveEdit = async (extractionId) => {
        try {
            const response = await fetch(`/api/extractions/${extractionId}/verify/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(editValues)
            });

            if (!response.ok) {
                throw new Error('Failed to save correction');
            }

            const result = await response.json();
            
            // Update local state
            setExtractions(prev => prev.map(extraction => 
                extraction.id === extractionId 
                    ? { 
                        ...extraction, 
                        corrected_value: editValues.corrected_value,
                        correction_reason: editValues.correction_reason,
                        is_verified: true,
                        verified_at: new Date().toISOString()
                      }
                    : extraction
            ));

            // Update document status if needed
            if (result.document_status !== document.status) {
                setDocument(prev => ({ ...prev, status: result.document_status }));
            }

            setEditingField(null);
            setEditValues({});

        } catch (err) {
            setError(err.message);
        }
    };

    const handleVerifyField = async (extractionId) => {
        try {
            setVerifyingFields(prev => new Set([...prev, extractionId]));

            const response = await fetch(`/api/extractions/${extractionId}/verify/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({})
            });

            if (!response.ok) {
                throw new Error('Failed to verify field');
            }

            const result = await response.json();

            // Update local state
            setExtractions(prev => prev.map(extraction => 
                extraction.id === extractionId 
                    ? { ...extraction, is_verified: true, verified_at: new Date().toISOString() }
                    : extraction
            ));

            // Update document status if needed
            if (result.document_status !== document.status) {
                setDocument(prev => ({ ...prev, status: result.document_status }));
                if (result.document_status === 'approved' && onReviewComplete) {
                    onReviewComplete(document);
                }
            }

        } catch (err) {
            setError(err.message);
        } finally {
            setVerifyingFields(prev => {
                const updated = new Set(prev);
                updated.delete(extractionId);
                return updated;
            });
        }
    };

    const getStatusBadge = (status) => {
        const variants = {
            'uploaded': 'secondary',
            'processing': 'warning',
            'ocr_complete': 'info',
            'extraction_complete': 'info',
            'review_required': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'error': 'danger'
        };

        return <Badge bg={variants[status] || 'secondary'}>{status.replace('_', ' ').toUpperCase()}</Badge>;
    };

    const getConfidenceBadge = (confidence) => {
        if (confidence >= 0.9) return <Badge bg="success">High ({(confidence * 100).toFixed(1)}%)</Badge>;
        if (confidence >= 0.7) return <Badge bg="warning">Medium ({(confidence * 100).toFixed(1)}%)</Badge>;
        return <Badge bg="danger">Low ({(confidence * 100).toFixed(1)}%)</Badge>;
    };

    const formatFieldType = (type) => {
        return type.charAt(0).toUpperCase() + type.slice(1);
    };

    if (loading) {
        return (
            <Container className="text-center py-5" data-testid="document-review-loading">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading...</span>
                </Spinner>
                <p className="mt-2">Loading document details...</p>
            </Container>
        );
    }

    if (error) {
        return (
            <Container data-testid="document-review-error">
                <Alert variant="danger">
                    <AlertTriangle className="me-2" size={20} />
                    Error: {error}
                </Alert>
            </Container>
        );
    }

    if (!document) {
        return (
            <Container data-testid="document-review-not-found">
                <Alert variant="warning">Document not found</Alert>
            </Container>
        );
    }

    const unverifiedCount = extractions.filter(ext => !ext.is_verified).length;
    const totalExtractions = extractions.length;

    return (
        <Container fluid className="py-4" data-testid="document-review-interface">
            {/* Document Header */}
            <Row className="mb-4">
                <Col>
                    <Card data-testid="document-review-header">
                        <Card.Header className="d-flex justify-content-between align-items-center">
                            <div>
                                <h5 className="mb-1">
                                    <FileText className="me-2" size={20} />
                                    {document.original_filename}
                                </h5>
                                <div className="d-flex gap-3 text-muted small">
                                    <span>Size: {document.file_size_mb} MB</span>
                                    <span>Type: {document.document_type_name || 'Unknown'}</span>
                                    <span>Uploaded: {new Date(document.created_at).toLocaleDateString()}</span>
                                </div>
                            </div>
                            <div className="text-end">
                                {getStatusBadge(document.status)}
                                {document.ocr_confidence && (
                                    <div className="mt-1">
                                        <small className="text-muted">OCR Confidence: </small>
                                        {getConfidenceBadge(document.ocr_confidence)}
                                    </div>
                                )}
                            </div>
                        </Card.Header>
                    </Card>
                </Col>
            </Row>

            {/* Review Progress */}
            {totalExtractions > 0 && (
                <Row className="mb-4">
                    <Col>
                        <Card data-testid="review-progress-card">
                            <Card.Body>
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 className="mb-1">Review Progress</h6>
                                        <p className="mb-0 text-muted">
                                            {totalExtractions - unverifiedCount} of {totalExtractions} fields verified
                                        </p>
                                    </div>
                                    <div className="text-end">
                                        <div className="progress" style={{ width: '200px', height: '8px' }}>
                                            <div 
                                                className="progress-bar bg-success" 
                                                style={{ 
                                                    width: `${((totalExtractions - unverifiedCount) / totalExtractions) * 100}%` 
                                                }}
                                            />
                                        </div>
                                        <small className="text-muted mt-1">
                                            {Math.round(((totalExtractions - unverifiedCount) / totalExtractions) * 100)}% complete
                                        </small>
                                    </div>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            )}

            <Row>
                {/* Extracted Fields */}
                <Col lg={8}>
                    <Card data-testid="extracted-fields-card">
                        <Card.Header className="d-flex justify-content-between align-items-center">
                            <h6 className="mb-0">Extracted Fields</h6>
                            {unverifiedCount > 0 && (
                                <Badge bg="warning">{unverifiedCount} pending review</Badge>
                            )}
                        </Card.Header>
                        <Card.Body>
                            {extractions.length === 0 ? (
                                <Alert variant="info" data-testid="no-extractions-alert">
                                    No data fields were extracted from this document.
                                </Alert>
                            ) : (
                                <div className="extraction-fields" data-testid="extraction-fields-list">
                                    {extractions.map((extraction) => (
                                        <Card key={extraction.id} className="mb-3 border-start border-3" 
                                              style={{ borderLeftColor: extraction.is_verified ? '#198754' : '#ffc107' }}
                                              data-testid={`extraction-field-${extraction.field_name}`}>
                                            <Card.Body>
                                                <Row>
                                                    <Col md={3}>
                                                        <strong>{extraction.field_name.replace('_', ' ').toUpperCase()}</strong>
                                                        <div className="small text-muted">
                                                            {formatFieldType(extraction.field_type)}
                                                        </div>
                                                    </Col>
                                                    <Col md={5}>
                                                        {editingField === extraction.id ? (
                                                            <Form.Group>
                                                                <Form.Control
                                                                    type="text"
                                                                    value={editValues.corrected_value}
                                                                    onChange={(e) => setEditValues(prev => ({
                                                                        ...prev,
                                                                        corrected_value: e.target.value
                                                                    }))}
                                                                    data-testid={`edit-field-${extraction.field_name}`}
                                                                />
                                                                <Form.Control
                                                                    as="textarea"
                                                                    rows={2}
                                                                    placeholder="Reason for correction (optional)"
                                                                    className="mt-2"
                                                                    value={editValues.correction_reason}
                                                                    onChange={(e) => setEditValues(prev => ({
                                                                        ...prev,
                                                                        correction_reason: e.target.value
                                                                    }))}
                                                                    data-testid={`correction-reason-${extraction.field_name}`}
                                                                />
                                                            </Form.Group>
                                                        ) : (
                                                            <div>
                                                                <div className="fw-medium">
                                                                    {extraction.corrected_value || extraction.field_value}
                                                                </div>
                                                                {extraction.corrected_value && (
                                                                    <div className="small text-muted">
                                                                        Original: {extraction.original_value}
                                                                    </div>
                                                                )}
                                                                {extraction.correction_reason && (
                                                                    <div className="small text-info mt-1">
                                                                        Correction: {extraction.correction_reason}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </Col>
                                                    <Col md={2} className="text-center">
                                                        {getConfidenceBadge(extraction.confidence)}
                                                    </Col>
                                                    <Col md={2} className="text-end">
                                                        {extraction.is_verified ? (
                                                            <Badge bg="success" className="d-flex align-items-center gap-1">
                                                                <CheckCircle size={14} />
                                                                Verified
                                                            </Badge>
                                                        ) : (
                                                            <ButtonGroup size="sm">
                                                                {editingField === extraction.id ? (
                                                                    <>
                                                                        <Button 
                                                                            variant="success" 
                                                                            onClick={() => handleSaveEdit(extraction.id)}
                                                                            data-testid={`save-edit-${extraction.field_name}`}
                                                                        >
                                                                            <Save size={14} />
                                                                        </Button>
                                                                        <Button 
                                                                            variant="secondary" 
                                                                            onClick={() => setEditingField(null)}
                                                                            data-testid={`cancel-edit-${extraction.field_name}`}
                                                                        >
                                                                            <X size={14} />
                                                                        </Button>
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <Button 
                                                                            variant="outline-success" 
                                                                            onClick={() => handleVerifyField(extraction.id)}
                                                                            disabled={verifyingFields.has(extraction.id)}
                                                                            data-testid={`verify-field-${extraction.field_name}`}
                                                                        >
                                                                            {verifyingFields.has(extraction.id) ? (
                                                                                <Spinner size="sm" />
                                                                            ) : (
                                                                                <CheckCircle size={14} />
                                                                            )}
                                                                        </Button>
                                                                        <Button 
                                                                            variant="outline-warning" 
                                                                            onClick={() => handleEditField(extraction)}
                                                                            data-testid={`edit-field-${extraction.field_name}`}
                                                                        >
                                                                            <Edit3 size={14} />
                                                                        </Button>
                                                                    </>
                                                                )}
                                                            </ButtonGroup>
                                                        )}
                                                    </Col>
                                                </Row>
                                            </Card.Body>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </Card.Body>
                    </Card>
                </Col>

                {/* Document Info & OCR Text */}
                <Col lg={4}>
                    {/* OCR Text */}
                    <Card className="mb-3" data-testid="ocr-text-card">
                        <Card.Header className="d-flex justify-content-between align-items-center">
                            <h6 className="mb-0">OCR Text</h6>
                            <Button 
                                variant="outline-primary" 
                                size="sm"
                                onClick={() => setShowOcrText(!showOcrText)}
                                data-testid="toggle-ocr-text"
                            >
                                <Eye size={14} className="me-1" />
                                {showOcrText ? 'Hide' : 'Show'}
                            </Button>
                        </Card.Header>
                        {showOcrText && (
                            <Card.Body>
                                <div 
                                    className="border rounded p-3 bg-light" 
                                    style={{ maxHeight: '300px', overflowY: 'auto', fontSize: '0.9em' }}
                                    data-testid="ocr-text-content"
                                >
                                    {document.ocr_text ? (
                                        <pre className="mb-0" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                            {document.ocr_text}
                                        </pre>
                                    ) : (
                                        <span className="text-muted">No OCR text available</span>
                                    )}
                                </div>
                            </Card.Body>
                        )}
                    </Card>

                    {/* Processing Logs */}
                    <Card data-testid="processing-logs-card">
                        <Card.Header>
                            <h6 className="mb-0">Processing History</h6>
                        </Card.Header>
                        <Card.Body>
                            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                {processingLogs.length === 0 ? (
                                    <p className="text-muted">No processing logs available</p>
                                ) : (
                                    <div className="processing-timeline" data-testid="processing-timeline">
                                        {processingLogs.map((log, index) => (
                                            <div key={log.id} className={`d-flex mb-3 ${index < processingLogs.length - 1 ? 'border-bottom pb-3' : ''}`}>
                                                <div className="me-3">
                                                    {log.status === 'completed' ? (
                                                        <CheckCircle size={16} className="text-success" />
                                                    ) : log.status === 'failed' ? (
                                                        <XCircle size={16} className="text-danger" />
                                                    ) : (
                                                        <Clock size={16} className="text-warning" />
                                                    )}
                                                </div>
                                                <div className="flex-grow-1">
                                                    <div className="small fw-medium">{log.step_display}</div>
                                                    <div className="small text-muted">{log.message}</div>
                                                    <div className="small text-muted">
                                                        {new Date(log.created_at).toLocaleString()}
                                                        {log.duration_seconds && (
                                                            <span> • {log.duration_seconds.toFixed(2)}s</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Container>
    );
};

export default DocumentReviewInterface;