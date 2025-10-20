import { TeamChatSidebar } from './TeamChatSidebar'
import { TeamChatWindow } from './TeamChatWindow'

interface TeamChatProps {
  mode: 'solo' | 'lan' | 'p2p'
}

export function TeamChat({ mode }: TeamChatProps) {
  // Convert network mode to chat mode (lan and p2p both use p2p for chat)
  const chatMode: 'solo' | 'p2p' = mode === 'solo' ? 'solo' : 'p2p'

  return (
    <div className="h-full w-full flex">
      {/* Sidebar */}
      <div className="w-80 flex-shrink-0 bg-gray-50/80 dark:bg-gray-800/50 backdrop-blur-xl border-r border-white/10 dark:border-gray-700/30">
        <TeamChatSidebar mode={chatMode} onModeChange={() => {}} />
      </div>

      {/* Main chat area */}
      <div className="flex-1">
        <TeamChatWindow mode={chatMode} />
      </div>
    </div>
  )
}
