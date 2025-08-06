import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Card, Badge } from 'react-bootstrap';
import { 
  Play, 
  Square, 
  FileText, 
  CheckCircle, 
  GitBranch, 
  Cpu, 
  Mail, 
  Link,
  Clock,
  User
} from 'lucide-react';

const iconMap = {
  'play-circle': Play,
  'stop-circle': Square,
  'file-text': FileText,
  'check-circle': CheckCircle,
  'git-branch': GitBranch,
  'cpu': Cpu,
  'mail': Mail,
  'link': Link,
};

const WorkflowNodeComponent = ({ data, selected }) => {
  const IconComponent = iconMap[data.icon] || Square;
  const nodeType = data.nodeType || {};

  const handleClick = () => {
    if (data.onSelect) {
      data.onSelect(data);
    }
  };

  // Determine if this node allows input/output connections
  const allowsInput = data.type !== 'start';
  const allowsOutput = data.type !== 'end';
  const allowsMultipleOutputs = nodeType.allows_multiple_outputs;

  return (
    <>
      {/* Input handle */}
      {allowsInput && (
        <Handle
          type="target"
          position={Position.Top}
          style={{
            background: '#555',
            width: 12,
            height: 12,
            border: '2px solid #fff'
          }}
        />
      )}
      
      <Card 
        className={`workflow-node ${selected ? 'selected' : ''}`}
        onClick={handleClick}
        style={{ 
          minWidth: '180px',
          cursor: 'pointer',
          border: selected ? `2px solid ${data.color}` : '1px solid #dee2e6',
          borderRadius: '8px',
          boxShadow: selected ? `0 0 0 2px ${data.color}20` : '0 2px 4px rgba(0,0,0,0.1)'
        }}
        data-testid={`workflow-node-${data.node_id}`}
      >
        <Card.Body className="p-2">
          <div className="d-flex align-items-center mb-2">
            <div 
              className="node-icon me-2 d-flex align-items-center justify-content-center rounded"
              style={{ 
                backgroundColor: data.color + '20',
                color: data.color,
                width: '28px',
                height: '28px'
              }}
            >
              <IconComponent size={14} />
            </div>
            <div className="flex-grow-1">
              <div className="fw-semibold small text-truncate" title={data.name}>
                {data.name}
              </div>
              <div className="text-muted" style={{ fontSize: '0.7rem' }}>
                {data.type}
              </div>
            </div>
          </div>
          
          {/* Node status indicators */}
          <div className="d-flex flex-wrap gap-1 mb-1">
            {nodeType.requires_user_action && (
              <Badge bg="warning" style={{ fontSize: '0.6rem' }}>
                <User size={8} className="me-1" />
                Manual
              </Badge>
            )}
            {data.timeout_seconds && data.timeout_seconds !== 300 && (
              <Badge bg="info" style={{ fontSize: '0.6rem' }}>
                <Clock size={8} className="me-1" />
                {data.timeout_seconds}s
              </Badge>
            )}
            {data.is_required === false && (
              <Badge bg="secondary" style={{ fontSize: '0.6rem' }}>
                Optional
              </Badge>
            )}
          </div>
          
          {/* Node description if available */}
          {data.description && (
            <div 
              className="text-muted small text-truncate" 
              style={{ fontSize: '0.65rem' }}
              title={data.description}
            >
              {data.description}
            </div>
          )}
          
          {/* Configuration preview */}
          {data.config && Object.keys(data.config).length > 0 && (
            <div className="mt-1">
              <Badge bg="light" text="dark" style={{ fontSize: '0.6rem' }}>
                Configured
              </Badge>
            </div>
          )}
        </Card.Body>
      </Card>
      
      {/* Output handle(s) */}
      {allowsOutput && (
        <>
          <Handle
            type="source"
            position={Position.Bottom}
            style={{
              background: data.color,
              width: 12,
              height: 12,
              border: '2px solid #fff'
            }}
          />
          
          {/* Additional output handles for nodes that support multiple outputs */}
          {allowsMultipleOutputs && data.type === 'decision' && (
            <>
              <Handle
                type="source"
                position={Position.Right}
                id="yes"
                style={{
                  background: '#28a745',
                  width: 10,
                  height: 10,
                  border: '2px solid #fff',
                  right: -5,
                  top: '40%'
                }}
              />
              <Handle
                type="source"
                position={Position.Left}
                id="no"
                style={{
                  background: '#dc3545',
                  width: 10,
                  height: 10,
                  border: '2px solid #fff',
                  left: -5,
                  top: '40%'
                }}
              />
            </>
          )}
          
          {allowsMultipleOutputs && data.type === 'approval' && (
            <>
              <Handle
                type="source"
                position={Position.Right}
                id="approved"
                style={{
                  background: '#28a745',
                  width: 10,
                  height: 10,
                  border: '2px solid #fff',
                  right: -5,
                  top: '40%'
                }}
              />
              <Handle
                type="source"
                position={Position.Left}
                id="rejected"
                style={{
                  background: '#dc3545',
                  width: 10,
                  height: 10,
                  border: '2px solid #fff',
                  left: -5,
                  top: '40%'
                }}
              />
            </>
          )}
        </>
      )}
      
      <style jsx>{`
        .workflow-node {
          transition: all 0.2s ease;
        }
        
        .workflow-node:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        }
        
        .workflow-node.selected {
          transform: translateY(-1px);
        }
        
        .node-icon {
          transition: transform 0.2s ease;
        }
        
        .workflow-node:hover .node-icon {
          transform: scale(1.1);
        }
      `}</style>
    </>
  );
};

export default memo(WorkflowNodeComponent);