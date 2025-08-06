import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Button, 
  Badge, 
  Accordion, 
  InputGroup,
  Row,
  Col 
} from 'react-bootstrap';
import { Settings, Save, Trash2, Copy } from 'lucide-react';

const WorkflowPropertiesPanel = ({ selectedElement, onUpdateElement }) => {
  const [localData, setLocalData] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Update local data when selection changes
  useEffect(() => {
    if (selectedElement) {
      setLocalData({ ...selectedElement.data });
      setHasChanges(false);
    } else {
      setLocalData(null);
      setHasChanges(false);
    }
  }, [selectedElement]);

  // Handle form field changes
  const handleFieldChange = (field, value) => {
    if (!localData) return;
    
    const updatedData = { ...localData };
    
    // Handle nested config changes
    if (field.startsWith('config.')) {
      const configField = field.replace('config.', '');
      updatedData.config = updatedData.config || {};
      updatedData.config[configField] = value;
    } else {
      updatedData[field] = value;
    }
    
    setLocalData(updatedData);
    setHasChanges(true);
  };

  // Save changes
  const handleSave = () => {
    if (localData && onUpdateElement) {
      onUpdateElement(localData);
      setHasChanges(false);
    }
  };

  // Render form field based on schema type
  const renderFormField = (fieldName, schema, currentValue) => {
    const fieldKey = `config.${fieldName}`;
    const value = currentValue !== undefined ? currentValue : schema.default;

    switch (schema.type) {
      case 'text':
        return (
          <Form.Control
            type="text"
            value={value || ''}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={schema.placeholder}
          />
        );
      
      case 'textarea':
        return (
          <Form.Control
            as="textarea"
            rows={3}
            value={value || ''}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={schema.placeholder}
          />
        );
      
      case 'number':
        return (
          <Form.Control
            type="number"
            value={value || schema.default || 0}
            onChange={(e) => handleFieldChange(fieldKey, parseInt(e.target.value))}
            min={schema.min}
            max={schema.max}
          />
        );
      
      case 'select':
        return (
          <Form.Select
            value={value || schema.default || ''}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
          >
            <option value="">Select...</option>
            {schema.options?.map(option => (
              <option key={option} value={option}>
                {option.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </Form.Select>
        );
      
      case 'multiselect':
        const selectedValues = Array.isArray(value) ? value : (schema.default || []);
        return (
          <div>
            {schema.options?.map(option => (
              <Form.Check
                key={option}
                type="checkbox"
                id={`${fieldName}-${option}`}
                label={option.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                checked={selectedValues.includes(option)}
                onChange={(e) => {
                  const newValues = e.target.checked
                    ? [...selectedValues, option]
                    : selectedValues.filter(v => v !== option);
                  handleFieldChange(fieldKey, newValues);
                }}
              />
            ))}
          </div>
        );
      
      case 'slider':
        return (
          <div>
            <Form.Range
              min={schema.min || 0}
              max={schema.max || 100}
              step={schema.step || 1}
              value={value || schema.default || 0}
              onChange={(e) => handleFieldChange(fieldKey, parseFloat(e.target.value))}
            />
            <div className="d-flex justify-content-between small text-muted">
              <span>{schema.min || 0}</span>
              <span className="fw-semibold">{value || schema.default || 0}</span>
              <span>{schema.max || 100}</span>
            </div>
          </div>
        );
      
      case 'email_list':
        return (
          <Form.Control
            type="text"
            value={Array.isArray(value) ? value.join(', ') : value || ''}
            onChange={(e) => {
              const emails = e.target.value.split(',').map(email => email.trim()).filter(Boolean);
              handleFieldChange(fieldKey, emails);
            }}
            placeholder="Enter email addresses separated by commas"
          />
        );
      
      default:
        return (
          <Form.Control
            type="text"
            value={JSON.stringify(value || {})}
            onChange={(e) => {
              try {
                const parsedValue = JSON.parse(e.target.value);
                handleFieldChange(fieldKey, parsedValue);
              } catch (err) {
                // Invalid JSON, ignore
              }
            }}
            placeholder="JSON configuration"
          />
        );
    }
  };

  // Render node properties
  const renderNodeProperties = () => {
    if (!localData || selectedElement.type !== 'node') return null;

    const nodeType = localData.nodeType || {};
    const configSchema = nodeType.config_schema || {};

    return (
      <div data-testid="node-properties-panel">
        <div className="d-flex align-items-center mb-3">
          <div 
            className="me-2 d-flex align-items-center justify-content-center rounded"
            style={{ 
              backgroundColor: localData.color + '20',
              color: localData.color,
              width: '32px',
              height: '32px'
            }}
          >
            <Settings size={16} />
          </div>
          <div>
            <h6 className="mb-0">{localData.name}</h6>
            <small className="text-muted">{localData.type} node</small>
          </div>
        </div>

        <Card className="mb-3">
          <Card.Header className="py-2">
            <small className="fw-semibold">Basic Properties</small>
          </Card.Header>
          <Card.Body className="py-2">
            <Form.Group className="mb-2">
              <Form.Label className="small fw-semibold">Node Name</Form.Label>
              <Form.Control
                size="sm"
                type="text"
                value={localData.name || ''}
                onChange={(e) => handleFieldChange('name', e.target.value)}
                data-testid="node-name-input"
              />
            </Form.Group>

            <Form.Group className="mb-2">
              <Form.Label className="small fw-semibold">Description</Form.Label>
              <Form.Control
                size="sm"
                as="textarea"
                rows={2}
                value={localData.description || ''}
                onChange={(e) => handleFieldChange('description', e.target.value)}
                data-testid="node-description-input"
              />
            </Form.Group>

            <Form.Group className="mb-2">
              <Form.Check
                type="checkbox"
                id="is-required"
                label="Required step"
                checked={localData.is_required !== false}
                onChange={(e) => handleFieldChange('is_required', e.target.checked)}
                data-testid="node-required-checkbox"
              />
            </Form.Group>
          </Card.Body>
        </Card>

        {/* Advanced Properties */}
        <Accordion className="mb-3">
          <Accordion.Item eventKey="0">
            <Accordion.Header>
              <small>Advanced Settings</small>
            </Accordion.Header>
            <Accordion.Body className="py-2">
              <Form.Group className="mb-2">
                <Form.Label className="small fw-semibold">Timeout (seconds)</Form.Label>
                <Form.Control
                  size="sm"
                  type="number"
                  value={localData.timeout_seconds || 300}
                  onChange={(e) => handleFieldChange('timeout_seconds', parseInt(e.target.value))}
                  min="1"
                  max="3600"
                  data-testid="node-timeout-input"
                />
              </Form.Group>

              <Form.Group className="mb-2">
                <Form.Label className="small fw-semibold">Retry Count</Form.Label>
                <Form.Control
                  size="sm"
                  type="number"
                  value={localData.retry_count || 3}
                  onChange={(e) => handleFieldChange('retry_count', parseInt(e.target.value))}
                  min="0"
                  max="10"
                  data-testid="node-retry-input"
                />
              </Form.Group>
            </Accordion.Body>
          </Accordion.Item>
        </Accordion>

        {/* Node-specific Configuration */}
        {Object.keys(configSchema).length > 0 && (
          <Card className="mb-3">
            <Card.Header className="py-2">
              <small className="fw-semibold">Node Configuration</small>
            </Card.Header>
            <Card.Body className="py-2">
              {Object.entries(configSchema).map(([fieldName, fieldSchema]) => (
                <Form.Group key={fieldName} className="mb-3">
                  <Form.Label className="small fw-semibold">
                    {fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Form.Label>
                  {renderFormField(fieldName, fieldSchema, localData.config?.[fieldName])}
                  {fieldSchema.description && (
                    <Form.Text className="text-muted" style={{ fontSize: '0.75rem' }}>
                      {fieldSchema.description}
                    </Form.Text>
                  )}
                </Form.Group>
              ))}
            </Card.Body>
          </Card>
        )}

        {/* Action Buttons */}
        <div className="d-grid gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges}
            data-testid="save-node-properties-btn"
          >
            <Save size={14} className="me-1" />
            Save Changes
          </Button>
        </div>
      </div>
    );
  };

  // Render edge properties
  const renderEdgeProperties = () => {
    if (!localData || selectedElement.type !== 'edge') return null;

    return (
      <div data-testid="edge-properties-panel">
        <div className="d-flex align-items-center mb-3">
          <div className="me-2">
            <Settings size={20} />
          </div>
          <div>
            <h6 className="mb-0">Connection</h6>
            <small className="text-muted">Edge properties</small>
          </div>
        </div>

        <Card>
          <Card.Body className="py-2">
            <Form.Group className="mb-2">
              <Form.Label className="small fw-semibold">Label</Form.Label>
              <Form.Control
                size="sm"
                type="text"
                value={localData.label || ''}
                onChange={(e) => handleFieldChange('label', e.target.value)}
                placeholder="Connection label"
              />
            </Form.Group>

            <Form.Group className="mb-2">
              <Form.Label className="small fw-semibold">Condition Type</Form.Label>
              <Form.Select
                size="sm"
                value={localData.data?.condition_type || 'always'}
                onChange={(e) => handleFieldChange('data.condition_type', e.target.value)}
              >
                <option value="always">Always</option>
                <option value="success">On Success</option>
                <option value="failure">On Failure</option>
                <option value="conditional">Conditional</option>
                <option value="approval_yes">Approval Yes</option>
                <option value="approval_no">Approval No</option>
              </Form.Select>
            </Form.Group>
          </Card.Body>
        </Card>

        <div className="d-grid gap-2 mt-3">
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges}
          >
            <Save size={14} className="me-1" />
            Save Changes
          </Button>
        </div>
      </div>
    );
  };

  if (!selectedElement) {
    return (
      <div className="text-center text-muted p-4" data-testid="no-selection-message">
        <Settings size={32} className="mb-2 opacity-50" />
        <p className="mb-0">Select a node or connection to view its properties</p>
      </div>
    );
  }

  return (
    <div className="properties-panel p-3" style={{ height: 'calc(100vh - 120px)', overflowY: 'auto' }}>
      {selectedElement.type === 'node' && renderNodeProperties()}
      {selectedElement.type === 'edge' && renderEdgeProperties()}
    </div>
  );
};

export default WorkflowPropertiesPanel;