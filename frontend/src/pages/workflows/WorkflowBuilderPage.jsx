import React, { useState, useEffect, useCallback } from 'react';
import { Container, Row, Col, Card, Button, Alert, Spinner } from 'react-bootstrap';
import ReactFlow, { 
  MiniMap, 
  Controls, 
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  ReactFlowProvider
} from 'reactflow';
import { Save, Play, Pause, Settings, Eye } from 'lucide-react';
import 'reactflow/dist/style.css';

import NavigationHeader from '../../components/organisms/NavigationHeader';
import WorkflowNodePalette from '../../components/organisms/WorkflowNodePalette';
import WorkflowNodeComponent from '../../components/molecules/WorkflowNodeComponent';
import WorkflowPropertiesPanel from '../../components/molecules/WorkflowPropertiesPanel';
import { workflowAPI } from '../../services/api/workflowAPI';

// Custom node types for ReactFlow
const nodeTypes = {
  workflowNode: WorkflowNodeComponent,
};

const WorkflowBuilderCanvas = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [workflow, setWorkflow] = useState(null);
  const [nodeTypes, setNodeTypes] = useState({});
  const [selectedElement, setSelectedElement] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const { setViewport, project } = useReactFlow();

  // Load workflow data
  useEffect(() => {
    const loadWorkflowData = async () => {
      try {
        setIsLoading(true);
        
        // Get workflow ID from URL params
        const urlParams = new URLSearchParams(window.location.search);
        const workflowId = urlParams.get('id');
        
        // Load node types
        const nodeTypesResponse = await workflowAPI.getNodeTypes();
        const nodeTypesGrouped = nodeTypesResponse.data;
        setNodeTypes(nodeTypesGrouped);

        if (workflowId) {
          // Load existing workflow
          const workflowResponse = await workflowAPI.getWorkflowCanvas(workflowId);
          const workflowData = workflowResponse.data;
          setWorkflow(workflowData);

          // Convert workflow nodes and edges to ReactFlow format
          const flowNodes = workflowData.nodes.map(node => ({
            id: node.id,
            type: 'workflowNode',
            position: node.position,
            data: {
              ...node,
              nodeType: nodeTypesGrouped[node.type]?.[0] || {},
              onSelect: (nodeData) => setSelectedElement({ type: 'node', data: nodeData })
            }
          }));

          const flowEdges = workflowData.edges.map(edge => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            data: edge
          }));

          setNodes(flowNodes);
          setEdges(flowEdges);
        }
      } catch (error) {
        console.error('Failed to load workflow data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadWorkflowData();
  }, []);

  // Handle edge connections
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ 
      ...params, 
      id: `e${params.source}-${params.target}`,
      data: { condition_type: 'always', label: '' }
    }, eds)),
    [setEdges]
  );

  // Handle node drag and drop from palette
  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = event.currentTarget.getBoundingClientRect();
      const nodeData = JSON.parse(event.dataTransfer.getData('application/nodedata'));
      const position = project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode = {
        id: `${nodeData.type}_${Date.now()}`,
        type: 'workflowNode',
        position,
        data: {
          node_id: `${nodeData.type}_${Date.now()}`,
          name: nodeData.name,
          type: nodeData.type,
          icon: nodeData.icon,
          color: nodeData.color,
          config: {},
          nodeType: nodeData,
          onSelect: (nodeData) => setSelectedElement({ type: 'node', data: nodeData })
        }
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [project, setNodes]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Save workflow
  const handleSave = async () => {
    if (!workflow) return;

    try {
      setIsSaving(true);
      setSaveMessage('');

      // Convert ReactFlow nodes and edges back to workflow format
      const workflowNodes = nodes.map(node => ({
        node_id: node.data.node_id,
        name: node.data.name,
        node_type: node.data.nodeType.id,
        position: node.position,
        config: node.data.config || {},
        description: node.data.description || '',
        is_required: node.data.is_required !== false,
        timeout_seconds: node.data.timeout_seconds || 300,
        retry_count: node.data.retry_count || 3
      }));

      const workflowEdges = edges.map(edge => ({
        source: edge.source,
        target: edge.target,
        condition_type: edge.data?.condition_type || 'always',
        condition_config: edge.data?.condition_config || {},
        label: edge.label || ''
      }));

      await workflowAPI.saveWorkflowCanvas(workflow.id, {
        nodes: workflowNodes,
        edges: workflowEdges
      });

      setSaveMessage('Workflow saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (error) {
      console.error('Failed to save workflow:', error);
      setSaveMessage('Failed to save workflow. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  // Activate workflow
  const handleActivate = async () => {
    if (!workflow) return;

    try {
      await workflowAPI.activateWorkflow(workflow.id);
      setWorkflow({ ...workflow, status: 'active' });
      setSaveMessage('Workflow activated successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (error) {
      console.error('Failed to activate workflow:', error);
      setSaveMessage('Failed to activate workflow. Please check the workflow structure.');
    }
  };

  // Handle node/edge selection
  const onSelectionChange = ({ nodes: selectedNodes, edges: selectedEdges }) => {
    if (selectedNodes.length > 0) {
      setSelectedElement({ type: 'node', data: selectedNodes[0].data });
    } else if (selectedEdges.length > 0) {
      setSelectedElement({ type: 'edge', data: selectedEdges[0] });
    } else {
      setSelectedElement(null);
    }
  };

  if (isLoading) {
    return (
      <>
        <NavigationHeader />
        <Container fluid className="py-4">
          <div className="d-flex justify-content-center align-items-center" style={{ height: '400px' }}>
            <Spinner animation="border" role="status">
              <span className="visually-hidden">Loading...</span>
            </Spinner>
          </div>
        </Container>
      </>
    );
  }

  return (
    <>
      <NavigationHeader />
      <Container fluid className="p-0">
        <Row className="g-0" style={{ height: '100vh' }}>
          {/* Node Palette Sidebar */}
          <Col md={3} className="bg-light border-end">
            <div className="p-3 border-bottom">
              <h5 className="mb-0" data-testid="workflow-palette-title">Workflow Components</h5>
            </div>
            <WorkflowNodePalette nodeTypes={nodeTypes} />
          </Col>

          {/* Main Canvas Area */}
          <Col md={6}>
            <div className="d-flex justify-content-between align-items-center p-3 border-bottom bg-white">
              <div>
                <h4 className="mb-1" data-testid="workflow-title">
                  {workflow?.name || 'New Workflow'}
                </h4>
                <small className="text-muted">
                  Status: <span className={`badge bg-${workflow?.status === 'active' ? 'success' : 'secondary'}`}>
                    {workflow?.status || 'draft'}
                  </span>
                </small>
              </div>
              <div className="d-flex gap-2">
                <Button 
                  variant="outline-primary" 
                  size="sm"
                  onClick={handleSave}
                  disabled={isSaving || !workflow}
                  data-testid="save-workflow-btn"
                >
                  <Save size={16} className="me-1" />
                  {isSaving ? 'Saving...' : 'Save'}
                </Button>
                <Button 
                  variant="success" 
                  size="sm"
                  onClick={handleActivate}
                  disabled={!workflow || workflow?.status === 'active'}
                  data-testid="activate-workflow-btn"
                >
                  <Play size={16} className="me-1" />
                  Activate
                </Button>
              </div>
            </div>

            {saveMessage && (
              <Alert variant={saveMessage.includes('Failed') ? 'danger' : 'success'} className="m-3 mb-0">
                {saveMessage}
              </Alert>
            )}

            <div 
              style={{ height: 'calc(100vh - 120px)' }}
              data-testid="workflow-builder-canvas"
              onDrop={onDrop}
              onDragOver={onDragOver}
            >
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onSelectionChange={onSelectionChange}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                defaultViewport={{ x: 0, y: 0, zoom: 1 }}
              >
                <MiniMap />
                <Controls />
                <Background variant="dots" gap={12} size={1} />
              </ReactFlow>
            </div>
          </Col>

          {/* Properties Panel */}
          <Col md={3} className="bg-light border-start">
            <div className="p-3 border-bottom">
              <h5 className="mb-0" data-testid="properties-panel-title">Properties</h5>
            </div>
            <WorkflowPropertiesPanel 
              selectedElement={selectedElement}
              onUpdateElement={(updatedElement) => {
                if (selectedElement.type === 'node') {
                  setNodes(nodes => nodes.map(node => 
                    node.id === selectedElement.data.id 
                      ? { ...node, data: { ...node.data, ...updatedElement } }
                      : node
                  ));
                }
                // Handle edge updates similarly
              }}
            />
          </Col>
        </Row>
      </Container>
    </>
  );
};

// Main component wrapped with ReactFlowProvider
const WorkflowBuilderPage = () => {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderCanvas />
    </ReactFlowProvider>
  );
};

export default WorkflowBuilderPage;