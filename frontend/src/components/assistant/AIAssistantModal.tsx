import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Bot,
  Send,
  Mic,
  Volume2,
  Pause,
  Square,
  RotateCcw,
  X,
  Sparkles,
  AlertTriangle,
  Building2,
  UserCheck,
  Pill,
  Navigation,
  FileText,
  Calendar,
  PhoneCall,
  Loader2,
  CheckCircle2,
  Radio,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { aiService, AIChatCard, AIChatResponse } from '../../services/aiService';
import { useTranslation } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { AudioRecorder } from '../../utils/audioRecorder';

export type VoiceState =
  | 'idle'
  | 'requesting_permission'
  | 'listening'
  | 'recording'
  | 'processing_speech'
  | 'transcript_ready'
  | 'waiting_ai'
  | 'generating_audio'
  | 'playing_response'
  | 'error';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  cards?: AIChatCard[];
  ragSources?: Array<{ document: string; section: string; content: string; score: number }>;
  timestamp: Date;
  audioBase64?: string;
  audioDuration?: number;
  isVoiceInput?: boolean;
  voiceProvider?: string;
  synthesizingAudio?: boolean;
}

interface AIAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery?: string;
}

export const AIAssistantModal: React.FC<AIAssistantModalProps> = ({ isOpen, onClose, initialQuery }) => {
  const { language: appLang, setLanguage: setAppLanguage, t } = useTranslation();
  const { user, patient } = useAuth();
  const navigate = useNavigate();

  // Assistant Chat State
  const [selectedLanguage, setSelectedLanguage] = useState<'ta' | 'en'>(appLang === 'ta' ? 'ta' : 'en');
  const [selectedVoice, setSelectedVoice] = useState<string>('Nalini');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);

  // Voice Interaction State Pipeline
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [voiceVolume, setVoiceVolume] = useState<number>(0.1);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [cloudVoiceStatus, setCloudVoiceStatus] = useState<any>(null);

  // Audio Playback State
  const [activeAudioMessageId, setActiveAudioMessageId] = useState<string | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState<boolean>(false);

  // Refs
  const audioRecorderRef = useRef<AudioRecorder | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const recordingTimerRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync assistant local state when application language context changes
  useEffect(() => {
    setSelectedLanguage(appLang === 'ta' ? 'ta' : 'en');
  }, [appLang]);

  // Handle bidirectional language switching: updates modal state and global context immediately
  const handleLanguageChange = (lang: 'ta' | 'en') => {
    setSelectedLanguage(lang);
    setAppLanguage(lang);
  };

  // Check Gnani Voice Engine Status on mount
  useEffect(() => {
    aiService
      .getVoiceStatus()
      .then((status) => {
        setCloudVoiceStatus(status);
        if (status?.default_voice) {
          setSelectedVoice(status.default_voice);
        }
      })
      .catch(() => {
        setCloudVoiceStatus({ is_live_cloud: false, provider: 'Offline Demo Mode' });
      });
  }, []);

  // Initialize bilingual welcome message
  const initWelcomeMessage = useCallback(() => {
    const welcomeText =
      selectedLanguage === 'ta'
        ? 'வணக்கம்! நான் நலம் (NALAM) AI நல்வாழ்வு உதவியாளர். அரசு ஆரம்ப சுகாதார நிலையங்கள் (PHC), மருத்துவர் வருகை, மருந்து இருப்பு மற்றும் அவசர சிகிச்சை தகவல்களை என்னிடம் தட்டச்சு செய்தோ அல்லது மைக்ரோஃபோன் மூலம் பேசியோ கேட்கலாம்.'
        : 'Hello! I am your NALAM AI Healthcare Assistant. Ask me to find nearby Primary Health Centres (PHC), verify doctor duty attendance, check medicine stock, or explain loss-minimizing recommendations. You can type or use the microphone to speak!';

    setMessages([
      {
        id: 'welcome',
        sender: 'assistant',
        text: welcomeText,
        timestamp: new Date(),
        voiceProvider: cloudVoiceStatus?.provider || 'NALAM Indic Engine',
      },
    ]);
  }, [selectedLanguage, cloudVoiceStatus]);

  useEffect(() => {
    if (messages.length === 0) {
      initWelcomeMessage();
    }
  }, [initWelcomeMessage, messages.length]);

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, voiceState]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRecorderRef.current) {
        audioRecorderRef.current.cancel();
      }
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current = null;
      }
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    };
  }, []);

  // Seed input with initialQuery when the modal opens
  useEffect(() => {
    if (isOpen && initialQuery) {
      setInput(initialQuery);
    }
  }, [isOpen, initialQuery]);

  // Reset / New Conversation
  const handleNewConversation = () => {
    stopCurrentAudio();
    if (audioRecorderRef.current) {
      audioRecorderRef.current.cancel();
    }
    setVoiceState('idle');
    setVoiceError(null);
    setInput('');
    setConversationId('');
    initWelcomeMessage();
  };

  // Audio Playback Utilities
  const stopCurrentAudio = () => {
    if (audioElementRef.current) {
      audioElementRef.current.pause();
      audioElementRef.current.currentTime = 0;
      audioElementRef.current = null;
    }
    setIsAudioPlaying(false);
    setActiveAudioMessageId(null);
    if (voiceState === 'playing_response') {
      setVoiceState('idle');
    }
  };

  const playBase64Audio = (msgId: string, base64Audio: string) => {
    stopCurrentAudio();

    try {
      const audio = new Audio(`data:audio/wav;base64,${base64Audio}`);
      audioElementRef.current = audio;
      setActiveAudioMessageId(msgId);
      setIsAudioPlaying(true);
      setVoiceState('playing_response');

      audio.onended = () => {
        setIsAudioPlaying(false);
        setActiveAudioMessageId(null);
        setVoiceState('idle');
      };

      audio.onerror = () => {
        setIsAudioPlaying(false);
        setActiveAudioMessageId(null);
        setVoiceState('idle');
        setVoiceError(
          selectedLanguage === 'ta'
            ? 'ஒலி பின்னணி இயக்கத்தில் பிழை ஏற்பட்டது.'
            : 'Audio playback failed in browser.'
        );
      };

      audio.play().catch((err) => {
        console.warn('Audio play was prevented by browser policy:', err);
        setIsAudioPlaying(false);
        setActiveAudioMessageId(null);
        setVoiceState('idle');
      });
    } catch {
      setVoiceError(
        selectedLanguage === 'ta'
          ? 'ஒலி இயக்கியைத் தொடங்க முடியவில்லை.'
          : 'Failed to initialize audio player.'
      );
      setVoiceState('idle');
    }
  };

  const handleTogglePlayAudio = async (msg: Message) => {
    // If this message is currently playing, pause/stop it
    if (activeAudioMessageId === msg.id && isAudioPlaying) {
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        setIsAudioPlaying(false);
        setVoiceState('idle');
      }
      return;
    }

    // If this message already has audio synthesized, play it
    if (msg.audioBase64) {
      playBase64Audio(msg.id, msg.audioBase64);
      return;
    }

    // Otherwise synthesize on demand via Gnani TTS
    try {
      setVoiceState('generating_audio');
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, synthesizingAudio: true } : m))
      );

      const synthRes = await aiService.synthesizeVoice(
        msg.text,
        selectedLanguage,
        selectedVoice
      );

      if (synthRes.audio_base64) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msg.id
              ? {
                  ...m,
                  audioBase64: synthRes.audio_base64,
                  audioDuration: synthRes.duration_seconds,
                  voiceProvider: synthRes.provider,
                  synthesizingAudio: false,
                }
              : m
          )
        );
        playBase64Audio(msg.id, synthRes.audio_base64);
      } else {
        setVoiceState('idle');
        setVoiceError(
          selectedLanguage === 'ta'
            ? 'குரல் பதிலை உருவாக்க முடியவில்லை.'
            : 'Unable to synthesize audio response.'
        );
      }
    } catch (err: any) {
      setVoiceState('idle');
      setVoiceError(
        selectedLanguage === 'ta'
          ? `குரல் உருவாக்கம் தோல்வியுற்றது: ${err.message || 'பிணையப் பிழை'}`
          : `Speech synthesis failed: ${err.message || 'Network error'}`
      );
    } finally {
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, synthesizingAudio: false } : m))
      );
    }
  };

  // -------------------------------------------------------------
  // Step A: Speech Capture via AudioRecorder
  // -------------------------------------------------------------
  const startRecording = async () => {
    stopCurrentAudio();
    setVoiceError(null);
    setVoiceState('requesting_permission');

    try {
      if (!audioRecorderRef.current) {
        audioRecorderRef.current = new AudioRecorder();
      }

      await audioRecorderRef.current.start((vol) => {
        setVoiceVolume(vol);
      });

      setVoiceState('recording');
      setRecordingSeconds(0);

      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev >= 25) {
            stopRecordingAndTranscribe();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err: any) {
      setVoiceState('error');
      setVoiceError(
        err.message ||
          (selectedLanguage === 'ta'
            ? 'மைக்ரோஃபோன் அனுமதி மறுக்கப்பட்டது. உலாவி அமைப்புகளில் அனுமதி வழங்கவும்.'
            : 'Microphone access denied. Please grant permission in browser settings.')
      );
    }
  };

  // -------------------------------------------------------------
  // Step B: Stop Recording & Transcribe with Gnani STT
  // -------------------------------------------------------------
  const stopRecordingAndTranscribe = async () => {
    if (!audioRecorderRef.current || !audioRecorderRef.current.isRecording()) return;

    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }

    setVoiceState('processing_speech');

    try {
      const { base64 } = await audioRecorderRef.current.stop();

      const result = await aiService.transcribeVoice(
        base64,
        selectedLanguage,
        'wav'
      );

      const transcript = (result.transcribed_text || '').trim();

      if (!transcript) {
        setVoiceState('error');
        setVoiceError(
          selectedLanguage === 'ta'
            ? 'குரல் தெளிவாகக் கேட்கவில்லை. தயவுசெய்து மீண்டும் பேசவும்.'
            : 'Could not clearly recognize speech. Please try speaking again.'
        );
        return;
      }

      setInput(transcript);
      setVoiceState('transcript_ready');

      // Auto-send voice input for seamless conversation
      handleSend(transcript, true);
    } catch (err: any) {
      setVoiceState('error');
      setVoiceError(
        selectedLanguage === 'ta'
          ? 'குரல் அறிதல் சேவை இணைக்க முடியவில்லை. உரை வடிவில் தட்டச்சு செய்யவும்.'
          : `Gnani STT speech recognition service failed: ${err.message || 'Offline mode'}`
      );
    }
  };

  const handleCancelVoice = () => {
    if (audioRecorderRef.current) {
      audioRecorderRef.current.cancel();
    }
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    setVoiceState('idle');
    setVoiceError(null);
  };

  // -------------------------------------------------------------
  // Step C & D: Send Message -> AI Agent & Tools -> Gnani TTS
  // -------------------------------------------------------------
  const handleSend = async (messageText?: string, isVoiceTurn: boolean = false) => {
    const textToSend = (messageText || input).trim();
    if (!textToSend || loading) return;

    stopCurrentAudio();

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date(),
      isVoiceInput: isVoiceTurn,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setVoiceState(isVoiceTurn ? 'waiting_ai' : 'idle');

    try {
      // Derive dynamic location context: registered patient profile village or active session village.
      // Never hardcode Tiruchengode!
      const activeLocationContext =
        patient?.village?.name ||
        (typeof window !== 'undefined'
          ? sessionStorage.getItem('nalam_active_village_name') ||
            (() => {
              try {
                const raw =
                  sessionStorage.getItem('nalam_active_village') ||
                  sessionStorage.getItem('carebridge_active_village');
                return raw ? JSON.parse(raw)?.name : undefined;
              } catch {
                return undefined;
              }
            })()
          : undefined);

      const response: AIChatResponse = await aiService.sendMessage({
        message: textToSend,
        conversation_id: conversationId || undefined,
        language: selectedLanguage,
        patient_id: patient?.id,
        village_id: patient?.village_id,
        location_context: activeLocationContext,
        user_role: user?.role || 'PATIENT',
        include_audio: isVoiceTurn,
        voice_name: selectedVoice,
      });

      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const botMessageId = (Date.now() + 1).toString();
      const botMessage: Message = {
        id: botMessageId,
        sender: 'assistant',
        text: response.response_text,
        cards: response.cards,
        ragSources: response.rag_sources,
        timestamp: new Date(),
        audioBase64: response.audio_base64,
        audioDuration: response.audio_duration,
        voiceProvider: response.voice_provider || cloudVoiceStatus?.provider,
      };

      setMessages((prev) => [...prev, botMessage]);

      if (isVoiceTurn && response.audio_base64) {
        playBase64Audio(botMessageId, response.audio_base64);
      } else {
        setVoiceState('idle');
      }
    } catch (error: any) {
      setVoiceState('error');
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text:
          selectedLanguage === 'ta'
            ? 'மன்னிக்கவும், சேவையகத்துடன் தொடர்புகொள்வதில் சிக்கல் ஏற்பட்டது. தயவுசெய்து சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.'
            : 'Sorry, I encountered an error communicating with the NALAM backend server. Please try again in a moment.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setVoiceError(error.message || 'Server communication error.');
    } finally {
      setLoading(false);
    }
  };

  const quickPrompts = [
    {
      en: 'Find nearby Primary Health Centres (PHC)',
      ta: 'அருகிலுள்ள ஆரம்ப சுகாதார நிலையங்களை காட்டு',
      icon: <Building2 className="w-3.5 h-3.5 text-teal-600" />,
    },
    {
      en: 'Is a doctor available at nearest facility today?',
      ta: 'அருகிலுள்ள PHC-யில் மருத்துவர் இன்று பணியில் உள்ளாரா?',
      icon: <UserCheck className="w-3.5 h-3.5 text-blue-600" />,
    },
    {
      en: 'Where can I get Paracetamol stock?',
      ta: 'பாராசிட்டமால் மருந்து எங்கு கிடைக்கும்?',
      icon: <Pill className="w-3.5 h-3.5 text-indigo-600" />,
    },
    {
      en: 'What is the Expected Trip Loss formula?',
      ta: 'வீண் பயண இழப்பு சூத்திரம் என்ன?',
      icon: <FileText className="w-3.5 h-3.5 text-purple-600" />,
    },
    {
      en: '108 Emergency Ambulance Protocol',
      ta: '108 அவசர ஆம்புலன்ஸ் உதவி',
      icon: <AlertTriangle className="w-3.5 h-3.5 text-red-600" />,
    },
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-slate-900/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl h-[94vh] max-h-[820px] flex flex-col border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-800 via-teal-900 to-slate-900 px-4 sm:px-6 py-3.5 text-white flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20 shadow-inner">
              <Bot className="w-6 h-6 text-teal-200" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-sm sm:text-base tracking-wide">
                  {t('aiTitle')}
                </h2>
                <span
                  className={`px-2 py-0.5 text-[10px] font-bold rounded-full flex items-center gap-1 ${
                    cloudVoiceStatus?.is_live_cloud
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-400/30'
                  }`}
                  title={cloudVoiceStatus?.provider || 'Gnani Indic Engine'}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      cloudVoiceStatus?.is_live_cloud ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                    }`}
                  />
                  {cloudVoiceStatus?.is_live_cloud ? 'Gnani.ai Cloud' : 'Indic Engine'}
                </span>
              </div>
              <p className="text-xs text-teal-100/80">
                {t('aiSubtitle')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Language Selector */}
            <div className="flex items-center bg-white/10 rounded-lg p-0.5 border border-white/15" role="group" aria-label="Language selection">
              <button
                type="button"
                onClick={() => handleLanguageChange('ta')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                  selectedLanguage === 'ta'
                    ? 'bg-teal-600 text-white shadow-xs'
                    : 'text-teal-200 hover:text-white'
                }`}
                aria-pressed={selectedLanguage === 'ta'}
                aria-label="தமிழ் மொழிக்கு மாற்றுக"
              >
                தமிழ்
              </button>
              <button
                type="button"
                onClick={() => handleLanguageChange('en')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                  selectedLanguage === 'en'
                    ? 'bg-teal-600 text-white shadow-xs'
                    : 'text-teal-200 hover:text-white'
                }`}
                aria-pressed={selectedLanguage === 'en'}
                aria-label="Switch to English"
              >
                English
              </button>
            </div>

            {/* New Conversation Button */}
            <button
              onClick={handleNewConversation}
              className="p-1.5 text-teal-200 hover:text-white rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
              title={t('aiNewConversation')}
              aria-label={t('aiNewConversation')}
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-1.5 text-teal-200 hover:text-white rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
              aria-label={t('aiCloseAssistant')}
              title={t('aiCloseAssistant')}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Suggestion Chips */}
        <div className="bg-slate-50 border-b border-slate-200/80 px-4 py-2 overflow-x-auto no-scrollbar flex items-center gap-2 shrink-0">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1 shrink-0">
            <Sparkles className="w-3 h-3 text-amber-500" />
            {t('aiSuggestions')}
          </span>
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(selectedLanguage === 'ta' ? p.ta : p.en)}
              className="px-3 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-full hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50/50 transition-all shadow-2xs whitespace-nowrap flex items-center gap-1.5 shrink-0 cursor-pointer"
            >
              {p.icon}
              {selectedLanguage === 'ta' ? p.ta : p.en}
            </button>
          ))}
        </div>

        {/* Conversational Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-slate-50/50">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[90%] sm:max-w-[82%] rounded-2xl p-4 shadow-2xs text-sm transition-all ${
                  msg.sender === 'user'
                    ? 'bg-teal-700 text-white rounded-br-xs'
                    : 'bg-white text-slate-800 border border-slate-200/90 rounded-bl-xs'
                }`}
              >
                {/* Message Header Badge */}
                <div className="flex items-center justify-between gap-3 mb-1.5 pb-1 border-b border-slate-100/20 text-[10px]">
                  <span className="font-semibold uppercase tracking-wider opacity-80 flex items-center gap-1">
                    {msg.sender === 'user' ? (
                      <>
                        {msg.isVoiceInput && (
                          <span className="flex items-center gap-1 px-1.5 py-0.2 bg-teal-800 rounded text-teal-200 font-medium">
                            <Mic className="w-2.5 h-2.5" /> {t('aiSpeaker_spoken')}
                          </span>
                        )}
                        {t('aiSpeaker_you')}
                      </>
                    ) : (
                      <>
                        <Bot className="w-3 h-3 text-teal-600" />
                        NALAM AI
                      </>
                    )}
                  </span>
                  <span className="opacity-70">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                {/* Message Body */}
                <div className="whitespace-pre-line leading-relaxed font-normal">{msg.text}</div>

                {/* Structured Cards */}
                {msg.cards && msg.cards.length > 0 && (
                  <div className="mt-3.5 space-y-2.5 pt-2 border-t border-slate-100">
                    {msg.cards.map((card, cIdx) => (
                      <div
                        key={cIdx}
                        className={`p-3.5 rounded-xl border text-xs transition-all ${
                          card.type === 'EMERGENCY'
                            ? 'bg-red-50/90 border-red-200 text-red-950'
                            : card.type === 'FACILITY'
                            ? 'bg-gradient-to-r from-teal-50/70 to-white border-teal-200/80 hover:border-teal-400'
                            : card.type === 'DOCTOR'
                            ? 'bg-gradient-to-r from-blue-50/70 to-white border-blue-200/80'
                            : card.type === 'RECOMMENDATION'
                            ? 'bg-gradient-to-r from-emerald-50/70 to-white border-emerald-300'
                            : 'bg-white border-slate-200'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                              {card.type === 'FACILITY' && <Building2 className="w-4 h-4 text-teal-600" />}
                              {card.type === 'DOCTOR' && <UserCheck className="w-4 h-4 text-blue-600" />}
                              {card.type === 'MEDICINE' && <Pill className="w-4 h-4 text-indigo-600" />}
                              {card.type === 'RECOMMENDATION' && <Navigation className="w-4 h-4 text-emerald-600" />}
                              {card.type === 'EMERGENCY' && <AlertTriangle className="w-4 h-4 text-red-600" />}
                              {card.title}
                            </div>
                            {card.subtitle && (
                              <div className="text-slate-500 text-[11px] mt-0.5 font-medium">{card.subtitle}</div>
                            )}
                          </div>

                          {card.badge && (
                            <span
                              className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-md shrink-0 ${
                                card.badge_color === 'green'
                                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                  : card.badge_color === 'yellow'
                                  ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                  : card.badge_color === 'red'
                                  ? 'bg-red-100 text-red-800 border border-red-200'
                                  : card.badge_color === 'purple'
                                  ? 'bg-purple-100 text-purple-800 border border-purple-200'
                                  : 'bg-blue-100 text-blue-800 border border-blue-200'
                              }`}
                            >
                              {card.badge}
                            </span>
                          )}
                        </div>

                        {/* Card Details */}
                        {card.details && Object.keys(card.details).length > 0 && (
                          <div className="mt-2 text-slate-600 space-y-1">
                            {card.details.address && (
                              <div className="text-[11px] text-slate-500 line-clamp-1">
                                📍 {card.details.address}
                              </div>
                            )}
                            {card.details.doctor_name && (
                              <div className="text-[11px] font-medium text-slate-700">
                                👨‍⚕️ {card.details.doctor_name} ({card.details.doctor_status}) • {card.details.doctor_hours}
                              </div>
                            )}
                            {card.details.expected_loss !== undefined && (
                              <div className="text-[11px] font-semibold text-emerald-800 bg-emerald-100/60 px-2 py-1 rounded">
                                📉 {t('aiExpectedLoss')}:{' '}
                                <span className="underline">{card.details.expected_loss} units</span> (Risk:{' '}
                                {card.details.failure_risk_pct}%)
                              </div>
                            )}
                            {card.details.services && Array.isArray(card.details.services) && (
                              <div className="flex flex-wrap gap-1 mt-1.5">
                                {card.details.services.slice(0, 4).map((s: string, sI: number) => (
                                  <span
                                    key={sI}
                                    className="px-1.5 py-0.5 text-[10px] bg-slate-100 text-slate-600 rounded font-medium"
                                  >
                                    {s}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Card Action Button */}
                        {card.action && (
                          <div className="mt-2.5 pt-2 border-t border-slate-200/50 flex justify-end">
                            {card.action.type === 'CALL' ? (
                              <a
                                href="tel:108"
                                className="px-3 py-1 bg-red-600 text-white rounded-lg font-bold text-xs hover:bg-red-700 flex items-center gap-1.5 shadow-sm"
                              >
                                <PhoneCall className="w-3 h-3" />
                                {card.action.label}
                              </a>
                            ) : (
                              <button
                                type="button"
                                onClick={() => {
                                  onClose();
                                  navigate('/appointments');
                                }}
                                className="px-3 py-1 bg-teal-700 text-white rounded-lg font-semibold text-xs hover:bg-teal-800 flex items-center gap-1 shadow-2xs transition-colors cursor-pointer"
                              >
                                <Calendar className="w-3 h-3" />
                                {card.action.label}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Assistant Speech Playback Bar */}
                {msg.sender === 'assistant' && (
                  <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleTogglePlayAudio(msg)}
                        disabled={msg.synthesizingAudio}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all shadow-2xs ${
                          activeAudioMessageId === msg.id && isAudioPlaying
                            ? 'bg-teal-600 text-white'
                            : 'bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-700'
                        }`}
                        aria-label={t('aiListen')}
                      >
                        {msg.synthesizingAudio ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin text-teal-600" />
                            <span>{t('aiSynthesizing')}</span>
                          </>
                        ) : activeAudioMessageId === msg.id && isAudioPlaying ? (
                          <>
                            <Pause className="w-3 h-3" />
                            <span>{t('aiPause')}</span>
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-3 h-3 text-teal-600" />
                            <span>{t('aiListen')}</span>
                          </>
                        )}
                      </button>

                      {activeAudioMessageId === msg.id && isAudioPlaying && (
                        <button
                          type="button"
                          onClick={stopCurrentAudio}
                          className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors"
                          title="Stop"
                          aria-label="Stop audio"
                        >
                          <Square className="w-3 h-3" />
                        </button>
                      )}

                      {/* Playing soundbar animation */}
                      {activeAudioMessageId === msg.id && isAudioPlaying && (
                        <div className="flex items-center gap-0.5 px-2">
                          <span className="w-1 h-3 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-1 h-4 bg-teal-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-1 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          <span className="w-1 h-5 bg-teal-700 rounded-full animate-bounce" style={{ animationDelay: '450ms' }} />
                        </div>
                      )}
                    </div>

                    <span className="text-[10px] text-slate-400 font-mono">
                      {msg.audioDuration ? `${msg.audioDuration}s` : ''}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex items-center gap-2.5 text-slate-500 text-xs p-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs max-w-md">
              <Loader2 className="w-4 h-4 animate-spin text-teal-600" />
              <span>{t('aiLoading')}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Dynamic Voice State & Animated Waveform Banner */}
        {voiceState !== 'idle' && (
          <div className="px-4 py-2.5 bg-gradient-to-r from-teal-900 to-slate-900 text-white flex items-center justify-between border-t border-teal-800 animate-fadeIn">
            <div className="flex items-center gap-3">
              {voiceState === 'recording' && (
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
                  <span className="text-xs font-bold text-red-400">
                    REC {recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds}s
                  </span>
                  {/* Dynamic Audio Waveform reacting to volume */}
                  <div className="flex items-center gap-0.5 ml-2 h-6">
                    {[0.2, 0.4, 0.7, 1.0, 0.8, 0.5, 0.3, 0.6, 0.9, 0.4, 0.2].map((weight, i) => {
                      const height = Math.max(4, Math.round(weight * voiceVolume * 24));
                      return (
                        <span
                          key={i}
                          className="w-1 bg-emerald-400 rounded-full transition-all duration-75"
                          style={{ height: `${height}px` }}
                        />
                      );
                    })}
                  </div>
                </div>
              )}

              {voiceState === 'requesting_permission' && (
                <span className="text-xs text-teal-200 flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {t('aiSpeech_requesting')}
                </span>
              )}

              {voiceState === 'processing_speech' && (
                <span className="text-xs text-teal-200 flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {t('aiSpeech_processing')}
                </span>
              )}

              {voiceState === 'transcript_ready' && (
                <span className="text-xs text-emerald-300 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {t('aiSpeech_ready')}
                </span>
              )}

              {voiceState === 'generating_audio' && (
                <span className="text-xs text-teal-200 flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {t('aiSpeech_generating')}
                </span>
              )}

              {voiceState === 'playing_response' && (
                <span className="text-xs text-emerald-300 flex items-center gap-2">
                  <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
                  {t('aiSpeech_playing')}
                </span>
              )}

              {voiceState === 'error' && (
                <span className="text-xs text-red-300 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  {voiceError || t('aiSpeech_errorFallback')}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {voiceState === 'recording' && (
                <button
                  type="button"
                  onClick={stopRecordingAndTranscribe}
                  className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center gap-1 cursor-pointer"
                >
                  <Square className="w-3 h-3 fill-current" />
                  {t('aiSpeech_doneButton')}
                </button>
              )}

              <button
                type="button"
                onClick={handleCancelVoice}
                className="p-1 text-slate-400 hover:text-white rounded cursor-pointer"
                title="Dismiss"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Input Bar */}
        <div className="p-3 bg-white border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            {/* Prominent Microphone Control */}
            <button
              type="button"
              onClick={voiceState === 'recording' ? stopRecordingAndTranscribe : startRecording}
              disabled={loading || voiceState === 'processing_speech'}
              className={`p-3 rounded-xl border transition-all cursor-pointer shadow-sm flex items-center justify-center ${
                voiceState === 'recording'
                  ? 'bg-red-600 text-white border-red-700 animate-pulse ring-4 ring-red-200'
                  : 'bg-gradient-to-r from-teal-50 to-emerald-50 text-teal-800 border-teal-300 hover:bg-teal-100'
              }`}
              title={
                voiceState === 'recording'
                  ? t('aiSpeech_micStop')
                  : t('aiSpeech_micTitle')
              }
              aria-label={
                voiceState === 'recording'
                  ? t('aiSpeech_micStop')
                  : t('aiSpeech_micTitle')
              }
            >
              {voiceState === 'recording' ? (
                <Square className="w-5 h-5 fill-current" />
              ) : (
                <Mic className="w-5 h-5 text-teal-700" />
              )}
            </button>

            {/* Chat Text Input */}
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('aiInputPlaceholder')}
              aria-label={t('aiInputPlaceholder')}
              className="flex-1 px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white transition-all placeholder:text-slate-400"
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-3 bg-teal-700 text-white rounded-xl hover:bg-teal-800 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md cursor-pointer"
              title={t('aiSendButton')}
              aria-label={t('aiSendButton')}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          {/* Legal / Clinical Disclaimer */}
          <div className="mt-2 text-[10px] text-slate-400 text-center leading-tight">
            {t('aiDisclaimer')}
          </div>
        </div>
      </div>
    </div>
  );
};
