import React from 'react';
import { Card, Badge } from 'react-bootstrap';
import { 
  Play, 
  Square, 
  FileText, 
  CheckCircle, 
  GitBranch, 
  Cpu, 
  Mail, 
  Link 
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

const WorkflowNodePalette = ({ nodeTypes }) => {
  const onDragStart = (event, nodeData) => {
    event.dataTransfer.setData('application/nodedata', JSON.stringify(nodeData));
    event.dataTransfer.effectAllowed = 'move';
  };

  const renderNodeType = (nodeType) => {
    const IconComponent = iconMap[nodeType.icon] || Square;
    
    return (
      <div
        key={nodeType.id}
        className="node-palette-item mb-2"
        draggable
        onDragStart={(event) => onDragStart(event, nodeType)}
        style={{ cursor: 'grab' }}
        data-testid={`node-type-${nodeType.type}`}
      >
        <Card className="border-0 shadow-sm h-100 workflow-node-card">
          <Card.Body className="p-2">
            <div className="d-flex align-items-center">
              <div 
                className="node-icon me-2 d-flex align-items-center justify-content-center rounded"
                style={{ 
                  backgroundColor: nodeType.color + '20',
                  color: nodeType.color,
                  width: '32px',
                  height: '32px'
                }}
              >
                <IconComponent size={16} />
              </div>
              <div className="flex-grow-1">
                <div className="fw-semibold small">{nodeType.name}</div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {nodeType.description}
                </div>
                <div className="mt-1">
                  {nodeType.requires_user_action && (
                    <Badge bg="warning" className="me-1" style={{ fontSize: '0.6rem' }}>
                      Manual
                    </Badge>
                  )}
                  {nodeType.allows_multiple_outputs && (
                    <Badge bg="info" style={{ fontSize: '0.6rem' }}>
                      Multi-output
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </Card.Body>
        </Card>
      </div>
    );
  };

  const typeDisplayNames = {
    start: 'Start Nodes',
    end: 'End Nodes',
    process: 'Processing',
    document: 'Document Processing',
    decision: 'Decision Points',
    approval: 'Approval Nodes',
    integration: 'Integrations',
    notification: 'Notifications'
  };

  return (
    <div className="workflow-node-palette" style={{ height: 'calc(100vh - 120px)', overflowY: 'auto' }}>
      <div className="p-3" data-testid="workflow-node-palette">
        {Object.entries(nodeTypes).map(([type, nodes]) => (
          <div key={type} className="mb-4">
            <h6 className="text-muted mb-2 text-uppercase small fw-bold">
              {typeDisplayNames[type] || type}
            </h6>
            {nodes.map(renderNodeType)}
          </div>
        ))}
        
        {Object.keys(nodeTypes).length === 0 && (
          <div className="text-center text-muted py-4">
            <p>Loading node types...</p>
          </div>
        )}
      </div>
      
      <style jsx>{`
        .workflow-node-card {
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .workflow-node-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        }
        
        .node-palette-item:active .workflow-node-card {
          transform: scale(0.95);
        }
        
        .node-icon {
          transition: all 0.2s ease;
        }
        
        .workflow-node-card:hover .node-icon {
          transform: scale(1.1);
        }
      `}</style>
    </div>
  );
};

export default WorkflowNodePalette;