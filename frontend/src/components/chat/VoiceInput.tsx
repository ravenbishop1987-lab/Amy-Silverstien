import { useState, useRef } from 'react'
import { Mic, MicOff, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

type BrowserSpeechRecognition = {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onend: (() => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  start: () => void
  stop: () => void
}

type SpeechRecognitionEvent = {
  resultIndex: number
  results: {
    length: number
    [index: number]: {
      isFinal: boolean
      [index: number]: { transcript: string }
    }
  }
}

type SpeechRecognitionErrorEvent = {
  error: string
}

declare global {
  interface Window {
    SpeechRecognition?: new () => BrowserSpeechRecognition
    webkitSpeechRecognition?: new () => BrowserSpeechRecognition
  }
}

interface Props {
  onTranscribed: (text: string) => void
  disabled?: boolean
}

type RecordState = 'idle' | 'recording' | 'processing'

export default function VoiceInput({ onTranscribed, disabled }: Props) {
  const [state, setState] = useState<RecordState>('idle')
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)

  const startRecording = async () => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Recognition) {
      toast.error('Voice input needs Chrome or Edge speech recognition.')
      return
    }

    const recognition = new Recognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'
    recognition.onresult = (event) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        if (result.isFinal) {
          transcript += result[0].transcript
        }
      }

      const text = transcript.trim()
      if (text) {
        onTranscribed(text)
      } else {
        toast.error("Hmm, I didn't catch that. Try again?")
      }
    }
    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        toast.error('Microphone access denied. Enable it in your browser settings.')
      } else {
        toast.error("Couldn't understand that. Try again!")
      }
      setState('idle')
    }
    recognition.onend = () => {
      recognitionRef.current = null
      setState('idle')
    }

    recognitionRef.current = recognition
    setState('recording')
    recognition.start()
  }

  const stopRecording = async () => {
    if (!recognitionRef.current) return
    setState('processing')
    recognitionRef.current.stop()
  }

  const handleClick = () => {
    if (state === 'idle') startRecording()
    else if (state === 'recording') stopRecording()
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || state === 'processing'}
      className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
        state === 'recording'
          ? 'bg-blush-400 text-white animate-pulse-soft'
          : state === 'processing'
          ? 'bg-cream-300 text-stone-400 cursor-wait'
          : 'bg-cream-200 text-stone-500 hover:bg-sage-100 hover:text-sage-600'
      }`}
      title={state === 'idle' ? 'Record voice message' : state === 'recording' ? 'Stop recording' : 'Processing...'}
    >
      {state === 'processing' ? (
        <Loader2 size={18} className="animate-spin" />
      ) : state === 'recording' ? (
        <MicOff size={18} />
      ) : (
        <Mic size={18} />
      )}
    </button>
  )
}
