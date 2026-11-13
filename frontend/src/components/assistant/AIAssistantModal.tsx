import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  Send,
  Mic,
  MicOff,
  Volume2,
  X,
  Sparkles,
  AlertTriangle,
  Building2,
  UserCheck,
  Pill,
  Navigation,
  FileText,
  Calendar,
  CheckCircle2,
  Clock,
  Loader2,
  PhoneCall,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { aiService, AIChatCard, AIChatResponse } from '../../services/aiService';
import { useTranslation } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  cards?: AIChatCard[];
  ragSources?: Array<{ document: string; section: string; content: string; score: number }>;
  timestamp: Date;
}

interface AIAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery?: string;
}

export const AIAssistantModal: React.FC<AIAssistantModalProps> = ({ isOpen, onClose, initialQuery }) => {
  const { language } = useTranslation();
  const { user, patient } = useAuth();
  const navigate = useNavigate();

  const [input, setInput] = useState(initialQuery || '');

  useEffect(() => {
    if (initialQuery) {
      setInput(initialQuery);
    }
  }, [initialQuery]);
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [conversationId, setConversationId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize with bilingual welcome message
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeText =
        language === 'ta'
          ? 'வணக்கம்! நான் NALAM AI நல்வாழ்வு உதவியாளர். அரசு ஆரம்ப சுகாதார நிலையங்கள் (PHC), மருத்துவர் இருப்பு, மருந்துகள் மற்றும் குறைந்த இழப்பு பரிந்துரைகள் பற்றி என்னிடம் கேட்கலாம்.'
          : 'Hello! I am your NALAM AI Healthcare Assistant. Ask me to find nearby Primary Health Centres (PHC), check verified doctor attendance, medicine stock, or explain loss-minimizing recommendations.';

      setMessages([
        {
          id: 'welcome',
          sender: 'assistant',
          text: welcomeText,
          timestamp: new Date(),
        },
      ]);
    }
  }, [language, messages.length]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const quickPrompts = [
    {
      en: 'Find a PHC near Tiruchengode',
      ta: 'திருச்செங்கோடு அருகே உள்ள ஆரம்ப சுகாதார நிலையம் எங்கே?',
      icon: <Building2 className="w-3.5 h-3.5 text-teal-600" />,
    },
    {
      en: 'Is a general physician available at the nearest PHC?',
      ta: 'அருகிலுள்ள PHC-யில் பொது மருத்துவர் பணியில் உள்ளாரா?',
      icon: <UserCheck className="w-3.5 h-3.5 text-blue-600" />,
    },
    {
      en: 'Where can I get Paracetamol near me?',
      ta: 'எனக்கு அருகில் பாராசிட்டமால் மருந்து எங்கு கிடைக்கும்?',
      icon: <Pill className="w-3.5 h-3.5 text-indigo-600" />,
    },
    {
      en: 'How does NALAM AI calculate healthcare recommendations?',
      ta: 'NALAM AI பரிந்துரைகளை எவ்வாறு கணக்கிடுகிறது?',
      icon: <FileText className="w-3.5 h-3.5 text-purple-600" />,
    },
    {
      en: '108 Emergency Ambulance Protocol',
      ta: '108 அவசர ஆம்புலன்ஸ் உதவி',
      icon: <AlertTriangle className="w-3.5 h-3.5 text-red-600" />,
    },
  ];

  const handleSend = async (messageText?: string) => {
    const textToSend = (messageText || input).trim();
    if (!textToSend || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!messageText) setInput('');
    setLoading(true);

    try {
      const response: AIChatResponse = await aiService.sendMessage({
        message: textToSend,
        conversation_id: conversationId || undefined,
        language: language === 'ta' ? 'ta' : 'en',
        patient_id: patient?.id,
        village_id: patient?.village_id,
        location_context: 'Tiruchengode',
        user_role: user?.role || 'PATIENT',
      });

      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: response.response_text,
        cards: response.cards,
        ragSources: response.rag_sources,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text:
          language === 'ta'
            ? 'மன்னிக்கவும், தகவலைப் பெறுவதில் சிக்கல் ஏற்பட்டது. தயவுசெய்து சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.'
            : 'Sorry, I encountered an error communicating with the healthcare server. Please try again in a moment.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // Browser speech recognition or fallback
  const handleToggleVoice = () => {
    if (isRecording) {
      setIsRecording(false);
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = language === 'ta' ? 'ta-IN' : 'en-IN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      setIsRecording(true);

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsRecording(false);
        handleSend(transcript);
      };

      recognition.onerror = () => {
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognition.start();
    } else {
      // Offline fallback: Use sample prompt
      const sample =
        language === 'ta'
          ? 'திருச்செங்கோடு அருகே உள்ள ஆரம்ப சுகாதார நிலையம் எங்கே?'
          : 'Find a PHC near Tiruchengode';
      setInput(sample);
      handleSend(sample);
    }
  };

  // Text-to-Speech output
  const handleSpeak = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      // Remove markdown bold and bullets for speech
      const plainText = text.replace(/[*#_`$]/g, '').trim();
      const utterance = new SpeechSynthesisUtterance(plainText);
      utterance.lang = language === 'ta' ? 'ta-IN' : 'en-IN';
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl h-[92vh] max-h-[760px] flex flex-col border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-700 via-teal-800 to-navy-900 px-5 py-3.5 text-white flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
              <Bot className="w-6 h-6 text-teal-200" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-base tracking-wide">
                  {language === 'ta' ? 'NALAM AI உதவியாளர்' : 'NALAM AI Assistant'}
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 rounded-full flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live
                </span>
              </div>
              <p className="text-xs text-teal-100/80">
                {language === 'ta'
                  ? 'வீண் பயணங்களைத் தவிர்ப்போம் • நேரடித் தகவல் வழிகாட்டி'
                  : 'No Wasted Trips • Uncertainty-Aware Navigation'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="p-1.5 text-teal-200 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
              aria-label="Close Assistant"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Suggestion Chips */}
        <div className="bg-slate-50 border-b border-slate-200/80 px-4 py-2.5 overflow-x-auto no-scrollbar flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1 shrink-0">
            <Sparkles className="w-3 h-3 text-amber-500" />
            {language === 'ta' ? 'விரைவு வினாக்கள்:' : 'Suggestions:'}
          </span>
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(language === 'ta' ? p.ta : p.en)}
              className="px-3 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-full hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50/50 transition-all shadow-2xs whitespace-nowrap flex items-center gap-1.5 shrink-0"
            >
              {p.icon}
              {language === 'ta' ? p.ta : p.en}
            </button>
          ))}
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/40">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl p-4 shadow-2xs text-sm ${
                  msg.sender === 'user'
                    ? 'bg-teal-700 text-white rounded-br-xs'
                    : 'bg-white text-slate-800 border border-slate-200/90 rounded-bl-xs'
                }`}
              >
                <div className="whitespace-pre-line leading-relaxed">{msg.text}</div>

                {/* Structured Cards Container */}
                {msg.cards && msg.cards.length > 0 && (
                  <div className="mt-3.5 space-y-2.5 pt-2 border-t border-slate-100">
                    {msg.cards.map((card, cIdx) => (
                      <div
                        key={cIdx}
                        className={`p-3.5 rounded-xl border text-xs transition-all ${
                          card.type === 'EMERGENCY'
                            ? 'bg-red-50/90 border-red-200 text-red-950'
                            : card.type === 'FACILITY'
                            ? 'bg-gradient-to-r from-teal-50/60 to-white border-teal-200/80 hover:border-teal-400'
                            : card.type === 'DOCTOR'
                            ? 'bg-gradient-to-r from-blue-50/60 to-white border-blue-200/80'
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

                        {/* Card details */}
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
                                📉 {language === 'ta' ? 'வீண் பயண இழப்பு குறியீடு' : 'Expected Trip Loss'}:{' '}
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
                                className="px-3 py-1 bg-teal-700 text-white rounded-lg font-semibold text-xs hover:bg-teal-800 flex items-center gap-1 shadow-2xs transition-colors"
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

                {/* Speak button on assistant replies */}
                {msg.sender === 'assistant' && (
                  <div className="mt-2 pt-1 flex items-center justify-between text-slate-400">
                    <span className="text-[10px]">
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleSpeak(msg.text)}
                      className="p-1 hover:text-teal-700 hover:bg-slate-100 rounded transition-colors"
                      title="Listen"
                    >
                      <Volume2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-slate-500 text-xs p-2">
              <Loader2 className="w-4 h-4 animate-spin text-teal-600" />
              <span>
                {language === 'ta'
                  ? 'தரவுத்தளத்தில் தேடி சரிபார்க்கிறது...'
                  : 'Executing database tools and calculating distances...'}
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-white border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <button
              type="button"
              onClick={handleToggleVoice}
              className={`p-2.5 rounded-xl border transition-all ${
                isRecording
                  ? 'bg-red-500 text-white border-red-600 animate-pulse'
                  : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
              }`}
              title={isRecording ? 'Stop Recording' : 'Voice Input (Gnani.ai Indic Voice)'}
            >
              {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                language === 'ta'
                  ? 'கேட்கவும்: "திருச்செங்கோடு அருகே உள்ள PHC எங்கே?"...'
                  : 'Ask: "Find a PHC near Tiruchengode", "Paracetamol stock"...'
              }
              className="flex-1 px-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white transition-all placeholder:text-slate-400"
            />

            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-2.5 bg-teal-700 text-white rounded-xl hover:bg-teal-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-2xs"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          {/* Legal / Clinical Disclaimer */}
          <div className="mt-2 text-[10px] text-slate-400 text-center leading-tight">
            {language === 'ta'
              ? 'NALAM AI வழிகாட்டுதல் தகவல் மட்டுமே. இது மருத்துவ நோயறிதல் அல்லது மருந்துச் சீட்டுகளை வழங்காது. அவசர நிலைக்கு 108 அழைக்கவும்.'
              : 'NALAM AI provides logistical coordination only. Does not provide clinical diagnosis or prescriptions. For medical emergencies, call 108 immediately.'}
          </div>
        </div>
      </div>
    </div>
  );
};
