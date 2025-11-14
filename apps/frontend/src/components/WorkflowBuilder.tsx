import { useCallback, useState } from 'react'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { ArrowLeft, Play, Save, HelpCircle, Info, ZoomIn, ZoomOut, Maximize2, Edit2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { WORKFLOW_DEFINITIONS } from './Automation/shared/templates'
import { nodeStyles } from './Automation/shared/styles'

interface WorkflowBuilderProps {
  templateId: string
  onBack: () => void
}

// Inner component that uses React Flow hooks
function WorkflowBuilderInner({ templateId, onBack }: WorkflowBuilderProps) {
  const template = WORKFLOW_DEFINITIONS[templateId] || WORKFLOW_DEFINITIONS['clinic-intake']
  const { zoomIn, zoomOut, fitView } = useReactFlow()

  const [nodes, setNodes, onNodesChange] = useNodesState(template.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(template.edges)
  const [isRunning, setIsRunning] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showViewControls, setShowViewControls] = useState(false)
  const [workflowName, setWorkflowName] = useState(template.name)
  const [isEditingName, setIsEditingName] = useState(false)
  const [isHoveringTitle, setIsHoveringTitle] = useState(false)

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const handleRun = async () => {
    setIsRunning(true)
    toast.loading('Running workflow...', { id: 'workflow-run' })

    try {
      // Send workflow to backend for execution
      const response = await fetch('/api/v1/automation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: templateId,
          name: workflowName,
          nodes: nodes.map(n => ({
            id: n.id,
            type: n.type,
            position: n.position,
            // Extract label text from JSX
            label: n.data.label?.props?.children?.[0]?.props?.children || 'Node'
          })),
          edges: edges.map(e => ({
            source: e.source,
            target: e.target
          }))
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const result = await response.json()

      toast.success(`Workflow completed! Processed ${result.steps_executed || nodes.length} steps.`, { id: 'workflow-run' })
    } catch (error) {
      console.error('Workflow execution error:', error)
      toast.error('Workflow execution failed. Check console for details.', { id: 'workflow-run' })
    } finally {
      setIsRunning(false)
    }
  }

  const handleSave = async () => {
    try {
      const response = await fetch('/api/v1/automation/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: templateId,
          name: workflowName,
          nodes,
          edges
        })
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      toast.success('Workflow saved successfully!')
    } catch (error) {
      console.error('Save error:', error)
      toast.error('Failed to save workflow')
    }
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              title="Back to templates"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
            <div>
              {/* Editable Workflow Title */}
              <div
                className="flex items-center gap-2 group"
                onMouseEnter={() => setIsHoveringTitle(true)}
                onMouseLeave={() => setIsHoveringTitle(false)}
              >
                {isEditingName ? (
                  <input
                    type="text"
                    value={workflowName}
                    onChange={(e) => setWorkflowName(e.target.value)}
                    onBlur={() => setIsEditingName(false)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') setIsEditingName(false)
                      if (e.key === 'Escape') {
                        setWorkflowName(template.name)
                        setIsEditingName(false)
                      }
                    }}
                    className="text-xl font-semibold text-gray-900 dark:text-gray-100 bg-transparent border-b-2 border-primary-500 focus:outline-none"
                    autoFocus
                  />
                ) : (
                  <h1
                    className="text-xl font-semibold text-gray-900 dark:text-gray-100 cursor-pointer"
                    onClick={() => setIsEditingName(true)}
                  >
                    {workflowName}
                  </h1>
                )}
                {!isEditingName && isHoveringTitle && (
                  <button
                    onClick={() => setIsEditingName(true)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Edit2 className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
                  </button>
                )}
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Drag nodes to customize • Click nodes to configure
              </p>
            </div>
          </div>

          {/* Right side action buttons - icon only */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              className="p-2.5 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
              title="Save workflow"
            >
              <Save className="w-5 h-5" />
            </button>
            <button
              onClick={handleRun}
              disabled={isRunning}
              className="p-2.5 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-400 text-white rounded-lg transition-colors"
              title={isRunning ? 'Running...' : 'Run workflow'}
            >
              <Play className={`w-5 h-5 ${isRunning ? 'animate-pulse' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          className="bg-gray-50 dark:bg-gray-900"
        >
          {/* Hide default controls - we'll add custom ones */}
          <MiniMap
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
            nodeColor={(node) => {
              if (node.style?.background) {
                return node.style.background as string
              }
              return '#3b82f6'
            }}
          />
          <Background
            variant={BackgroundVariant.Dots}
            gap={16}
            size={1}
            className="bg-gray-50 dark:bg-gray-900"
          />
        </ReactFlow>

        {/* View Controls Button - Positioned on top right edge of minimap */}
        <div className="absolute bottom-[160px] right-[20px] flex flex-col items-end gap-3">
          {/* View Controls Panel */}
          {showViewControls && (
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg animate-in slide-in-from-right">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">
                  View Controls
                </h3>
              </div>
              <div className="p-3 flex items-center gap-2">
                <button
                  onClick={() => zoomIn()}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Zoom in"
                >
                  <ZoomIn className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                </button>
                <button
                  onClick={() => zoomOut()}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Zoom out"
                >
                  <ZoomOut className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                </button>
                <button
                  onClick={() => fitView()}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Fit to view"
                >
                  <Maximize2 className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                </button>
              </div>
            </div>
          )}

          {/* Info Button */}
          <button
            onClick={() => setShowViewControls(!showViewControls)}
            className={`w-10 h-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full shadow-lg flex items-center justify-center transition-all hover:scale-110 ${
              showViewControls ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-300 dark:border-primary-700' : 'hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
            title="View controls"
          >
            <Info className={`w-5 h-5 ${showViewControls ? 'text-primary-600 dark:text-primary-400' : 'text-gray-600 dark:text-gray-400'}`} />
          </button>
        </div>

        {/* Help Button & Panel - Bottom Left */}
        <div className="absolute bottom-6 left-6 flex items-end gap-3">
          <button
            onClick={() => setShowHelp(!showHelp)}
            className={`w-10 h-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full shadow-lg flex items-center justify-center transition-all hover:scale-110 ${
              showHelp ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-300 dark:border-primary-700' : 'hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
            title="How this works"
          >
            <HelpCircle className={`w-5 h-5 ${showHelp ? 'text-primary-600 dark:text-primary-400' : 'text-gray-600 dark:text-gray-400'}`} />
          </button>

          {/* Expanded Help Panel */}
          {showHelp && (
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-w-xs animate-in slide-in-from-left">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                  How This Works
                </h3>
              </div>
              <div className="p-4 space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-start gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full mt-1 flex-shrink-0"></div>
                  <div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">Trigger:</span> Starts the workflow
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full mt-1 flex-shrink-0"></div>
                  <div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">Action:</span> Processes data
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-3 h-3 bg-purple-500 rounded-full mt-1 flex-shrink-0"></div>
                  <div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">AI:</span> Intelligent processing
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-3 h-3 bg-orange-500 rounded-full mt-1 flex-shrink-0"></div>
                  <div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">Output:</span> Saves results
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Wrapper component that provides React Flow context
export function WorkflowBuilder(props: WorkflowBuilderProps) {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderInner {...props} />
    </ReactFlowProvider>
  )
}
