import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Container, Row, Col, Button, Alert, Breadcrumb } from 'react-bootstrap';
import { ArrowLeft, CheckCircle } from 'lucide-react';
import DocumentReviewInterface from '../../components/molecules/DocumentReviewInterface';

const DocumentReviewPage = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [reviewComplete, setReviewComplete] = useState(false);

    const handleReviewComplete = (document) => {
        setReviewComplete(true);
        // Show success message for a moment, then redirect
        setTimeout(() => {
            navigate('/documents/processing');
        }, 2000);
    };

    const handleBackToProcessing = () => {
        navigate('/documents/processing');
    };

    return (
        <div data-testid="document-review-page">
            {/* Breadcrumb Navigation */}
            <Container fluid className="bg-light border-bottom py-2 mb-4">
                <Container>
                    <Row>
                        <Col>
                            <Breadcrumb className="mb-0">
                                <Breadcrumb.Item 
                                    onClick={() => navigate('/dashboard')}
                                    style={{ cursor: 'pointer' }}
                                >
                                    Dashboard
                                </Breadcrumb.Item>
                                <Breadcrumb.Item 
                                    onClick={() => navigate('/documents/processing')}
                                    style={{ cursor: 'pointer' }}
                                >
                                    Document Processing
                                </Breadcrumb.Item>
                                <Breadcrumb.Item active>Review Document</Breadcrumb.Item>
                            </Breadcrumb>
                        </Col>
                        <Col xs="auto">
                            <Button 
                                variant="outline-secondary" 
                                size="sm"
                                onClick={handleBackToProcessing}
                                data-testid="back-to-processing-btn"
                            >
                                <ArrowLeft size={14} className="me-1" />
                                Back to Processing
                            </Button>
                        </Col>
                    </Row>
                </Container>
            </Container>

            {/* Success Alert */}
            {reviewComplete && (
                <Container className="mb-4">
                    <Alert variant="success" className="d-flex align-items-center" data-testid="review-complete-alert">
                        <CheckCircle className="me-2" size={20} />
                        <div>
                            <strong>Review Complete!</strong> Document has been approved and is ready for processing.
                            Redirecting to document processing...
                        </div>
                    </Alert>
                </Container>
            )}

            {/* Document Review Interface */}
            <DocumentReviewInterface 
                documentId={id} 
                onReviewComplete={handleReviewComplete}
            />
        </div>
    );
};

export default DocumentReviewPage;