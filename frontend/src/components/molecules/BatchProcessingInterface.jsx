import React, { useState, useEffect } from 'react';
import { 
    Container, Row, Col, Card, Button, Alert, Form, 
    Table, Badge, Modal, Spinner, ProgressBar, ListGroup 
} from 'react-bootstrap';
import { 
    Play, Pause, Square, FileText, CheckCircle, 
    XCircle, Clock, Settings, Plus, Trash2 
} from 'lucide-react';

const BatchProcessingInterface = () => {
    const [batches, setBatches] = useState([]);
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [processingBatch, setProcessingBatch] = useState(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newBatch, setNewBatch] = useState({
        name: '',
        description: '',
        document_type: '',
        auto_approve_threshold: 0.8
    });
    const [selectedDocuments, setSelectedDocuments] = useState(new Set());

    useEffect(() => {
        loadBatches();
        loadAvailableDocuments();
    }, []);

    const loadBatches = async () => {
        try {
            const response = await fetch('/api/batches/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setBatches(data.results || data);
            }
        } catch (error) {
            console.error('Failed to load batches:', error);
        }
    };

    const loadAvailableDocuments = async () => {
        try {
            const response = await fetch('/api/documents/?status=uploaded', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setDocuments(data.results || data);
            }
        } catch (error) {
            console.error('Failed to load documents:', error);
        } finally {
            setLoading(false);
        }
    };

    const createBatch = async () => {
        try {
            if (!newBatch.name || selectedDocuments.size === 0) {
                alert('Please provide a batch name and select at least one document');
                return;
            }

            // Create the batch
            const batchResponse = await fetch('/api/batches/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    ...newBatch,
                    total_documents: selectedDocuments.size
                })
            });

            if (!batchResponse.ok) {
                throw new Error('Failed to create batch');
            }

            const batch = await batchResponse.json();

            // Add documents to batch
            const batchItems = Array.from(selectedDocuments).map((docId, index) => ({
                batch: batch.id,
                document: docId,
                processing_order: index + 1
            }));

            await Promise.all(batchItems.map(item => 
                fetch('/api/batch-items/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    },
                    body: JSON.stringify(item)
                })
            ));

            // Reset form and reload data
            setNewBatch({
                name: '',
                description: '',
                document_type: '',
                auto_approve_threshold: 0.8
            });
            setSelectedDocuments(new Set());
            setShowCreateModal(false);
            loadBatches();
            loadAvailableDocuments();

        } catch (error) {
            console.error('Failed to create batch:', error);
            alert('Failed to create batch');
        }
    };

    const startBatchProcessing = async (batchId) => {
        try {
            setProcessingBatch(batchId);

            const response = await fetch(`/api/batches/${batchId}/start_processing/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    use_openai: true
                })
            });

            if (!response.ok) {
                throw new Error('Failed to start batch processing');
            }

            // Reload batches to get updated status
            loadBatches();

        } catch (error) {
            console.error('Failed to start batch processing:', error);
            alert('Failed to start batch processing');
        } finally {
            setProcessingBatch(null);
        }
    };

    const deleteBatch = async (batchId) => {
        if (!confirm('Are you sure you want to delete this batch?')) {
            return;
        }

        try {
            const response = await fetch(`/api/batches/${batchId}/`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (response.ok) {
                loadBatches();
            }
        } catch (error) {
            console.error('Failed to delete batch:', error);
        }
    };

    const toggleDocumentSelection = (docId) => {
        const newSelection = new Set(selectedDocuments);
        if (newSelection.has(docId)) {
            newSelection.delete(docId);
        } else {
            newSelection.add(docId);
        }
        setSelectedDocuments(newSelection);
    };

    const getStatusBadge = (status) => {
        const variants = {
            'created': 'secondary',
            'processing': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'partially_completed': 'info'
        };
        return <Badge bg={variants[status] || 'secondary'}>{status.replace('_', ' ').toUpperCase()}</Badge>;
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'processing':
                return <Clock size={16} className="text-warning" />;
            case 'completed':
                return <CheckCircle size={16} className="text-success" />;
            case 'failed':
                return <XCircle size={16} className="text-danger" />;
            default:
                return <FileText size={16} className="text-muted" />;
        }
    };

    if (loading) {
        return (
            <Container className="text-center py-5" data-testid="batch-processing-loading">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading...</span>
                </Spinner>
                <p className="mt-2">Loading batch processing interface...</p>
            </Container>
        );
    }

    return (
        <Container fluid className="py-4" data-testid="batch-processing-interface">
            {/* Header */}
            <Row className="mb-4">
                <Col>
                    <div className="d-flex justify-content-between align-items-center">
                        <div>
                            <h4 className="mb-1">Batch Processing</h4>
                            <p className="text-muted mb-0">Process multiple documents together for efficiency</p>
                        </div>
                        <Button 
                            variant="primary"
                            onClick={() => setShowCreateModal(true)}
                            data-testid="create-batch-btn"
                        >
                            <Plus size={16} className="me-1" />
                            Create Batch
                        </Button>
                    </div>
                </Col>
            </Row>

            {/* Existing Batches */}
            <Row>
                <Col>
                    <Card data-testid="batches-card">
                        <Card.Header>
                            <h6 className="mb-0">Processing Batches</h6>
                        </Card.Header>
                        <Card.Body>
                            {batches.length === 0 ? (
                                <Alert variant="info" data-testid="no-batches-alert">
                                    No batches created yet. Create your first batch to process multiple documents together.
                                </Alert>
                            ) : (
                                <Table responsive hover data-testid="batches-table">
                                    <thead>
                                        <tr>
                                            <th>Batch Name</th>
                                            <th>Status</th>
                                            <th>Progress</th>
                                            <th>Documents</th>
                                            <th>Success Rate</th>
                                            <th>Created</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {batches.map((batch) => (
                                            <tr key={batch.id} data-testid={`batch-row-${batch.id}`}>
                                                <td>
                                                    <div className="d-flex align-items-center">
                                                        {getStatusIcon(batch.status)}
                                                        <div className="ms-2">
                                                            <div className="fw-medium">{batch.name}</div>
                                                            <small className="text-muted">{batch.description}</small>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td>{getStatusBadge(batch.status)}</td>
                                                <td>
                                                    <div>
                                                        <ProgressBar 
                                                            now={batch.completion_percentage} 
                                                            size="sm"
                                                            variant={batch.completion_percentage === 100 ? 'success' : 'info'}
                                                        />
                                                        <small>{batch.completion_percentage}%</small>
                                                    </div>
                                                </td>
                                                <td>
                                                    <span>{batch.processed_documents}/{batch.total_documents}</span>
                                                </td>
                                                <td>
                                                    {batch.processed_documents > 0 ? (
                                                        <Badge 
                                                            bg={batch.success_rate > 80 ? 'success' : batch.success_rate > 60 ? 'warning' : 'danger'}
                                                        >
                                                            {batch.success_rate}%
                                                        </Badge>
                                                    ) : (
                                                        <span className="text-muted">N/A</span>
                                                    )}
                                                </td>
                                                <td>
                                                    <small>{new Date(batch.created_at).toLocaleDateString()}</small>
                                                </td>
                                                <td>
                                                    <div className="d-flex gap-1">
                                                        {batch.status === 'created' && (
                                                            <Button
                                                                variant="outline-success"
                                                                size="sm"
                                                                onClick={() => startBatchProcessing(batch.id)}
                                                                disabled={processingBatch === batch.id}
                                                                data-testid={`start-batch-${batch.id}`}
                                                            >
                                                                {processingBatch === batch.id ? (
                                                                    <Spinner size="sm" />
                                                                ) : (
                                                                    <Play size={14} />
                                                                )}
                                                            </Button>
                                                        )}
                                                        <Button
                                                            variant="outline-danger"
                                                            size="sm"
                                                            onClick={() => deleteBatch(batch.id)}
                                                            data-testid={`delete-batch-${batch.id}`}
                                                        >
                                                            <Trash2 size={14} />
                                                        </Button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </Table>
                            )}
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Create Batch Modal */}
            <Modal show={showCreateModal} onHide={() => setShowCreateModal(false)} size="lg" data-testid="create-batch-modal">
                <Modal.Header closeButton>
                    <Modal.Title>Create New Batch</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <Form>
                        <Row>
                            <Col md={6}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Batch Name</Form.Label>
                                    <Form.Control
                                        type="text"
                                        value={newBatch.name}
                                        onChange={(e) => setNewBatch(prev => ({ ...prev, name: e.target.value }))}
                                        placeholder="Enter batch name"
                                        data-testid="batch-name-input"
                                    />
                                </Form.Group>
                            </Col>
                            <Col md={6}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Auto-approve Threshold</Form.Label>
                                    <Form.Range
                                        min={0}
                                        max={1}
                                        step={0.1}
                                        value={newBatch.auto_approve_threshold}
                                        onChange={(e) => setNewBatch(prev => ({ ...prev, auto_approve_threshold: parseFloat(e.target.value) }))}
                                        data-testid="auto-approve-threshold"
                                    />
                                    <Form.Text className="text-muted">
                                        Documents with confidence above {Math.round(newBatch.auto_approve_threshold * 100)}% will be auto-approved
                                    </Form.Text>
                                </Form.Group>
                            </Col>
                        </Row>

                        <Form.Group className="mb-3">
                            <Form.Label>Description (Optional)</Form.Label>
                            <Form.Control
                                as="textarea"
                                rows={2}
                                value={newBatch.description}
                                onChange={(e) => setNewBatch(prev => ({ ...prev, description: e.target.value }))}
                                placeholder="Describe this batch"
                                data-testid="batch-description-input"
                            />
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Select Documents ({selectedDocuments.size} selected)</Form.Label>
                            <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #dee2e6', borderRadius: '0.375rem' }}>
                                {documents.length === 0 ? (
                                    <div className="p-3 text-center text-muted">
                                        No uploaded documents available for batch processing
                                    </div>
                                ) : (
                                    <ListGroup variant="flush" data-testid="document-selection-list">
                                        {documents.map((doc) => (
                                            <ListGroup.Item 
                                                key={doc.id}
                                                className="d-flex justify-content-between align-items-center"
                                                data-testid={`document-item-${doc.id}`}
                                            >
                                                <div className="d-flex align-items-center">
                                                    <Form.Check
                                                        type="checkbox"
                                                        checked={selectedDocuments.has(doc.id)}
                                                        onChange={() => toggleDocumentSelection(doc.id)}
                                                        className="me-3"
                                                        data-testid={`document-checkbox-${doc.id}`}
                                                    />
                                                    <FileText size={16} className="text-muted me-2" />
                                                    <div>
                                                        <div className="fw-medium">{doc.original_filename}</div>
                                                        <small className="text-muted">
                                                            {doc.file_size_mb} MB • Uploaded {new Date(doc.created_at).toLocaleDateString()}
                                                        </small>
                                                    </div>
                                                </div>
                                                <Badge bg="light" text="dark">{doc.document_type_name || 'Unknown'}</Badge>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                )}
                            </div>
                        </Form.Group>
                    </Form>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
                        Cancel
                    </Button>
                    <Button 
                        variant="primary" 
                        onClick={createBatch}
                        disabled={!newBatch.name || selectedDocuments.size === 0}
                        data-testid="create-batch-submit"
                    >
                        Create Batch ({selectedDocuments.size} documents)
                    </Button>
                </Modal.Footer>
            </Modal>
        </Container>
    );
};

export default BatchProcessingInterface;