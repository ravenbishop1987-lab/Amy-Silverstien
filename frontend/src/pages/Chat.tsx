import { useParams } from 'react-router-dom'
import ChatInterface from '@/components/chat/ChatInterface'

export default function Chat() {
  const { conversationId } = useParams<{ conversationId?: string }>()
  return <ChatInterface conversationId={conversationId} />
}
