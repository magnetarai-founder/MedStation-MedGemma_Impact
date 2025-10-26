import { ResizableSidebar } from './ResizableSidebar'
import { TeamChatSidebar } from './TeamChatSidebar'
import { TeamChatWindow } from './TeamChatWindow'

interface TeamChatProps {
  mode: 'solo' | 'lan' | 'p2p'
}

export function TeamChat({ mode }: TeamChatProps) {
  // Convert network mode to chat mode (lan and p2p both use p2p for chat)
  const chatMode: 'solo' | 'p2p' = mode === 'solo' ? 'solo' : 'p2p'

  return (
    <ResizableSidebar
      initialWidth={320}
      minWidth={280}
      storageKey="ns.teamChatSidebarWidth"
      left={<TeamChatSidebar mode={chatMode} onModeChange={() => {}} />}
      right={<TeamChatWindow mode={chatMode} />}
    />
  )
}
