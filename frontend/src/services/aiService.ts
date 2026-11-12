import { apiRequest } from './apiClient';

export interface AIChatCard {
  type: 'FACILITY' | 'DOCTOR' | 'MEDICINE' | 'RECOMMENDATION' | 'APPOINTMENT' | 'EMERGENCY' | 'RAG_SOURCE' | 'DISCLAIMER';
  title: string;
  subtitle?: string;
  badge?: string;
  badge_color?: 'green' | 'yellow' | 'red' | 'blue' | 'purple';
  details: Record<string, any>;
  action?: {
    label: string;
    type: string;
    facility_id?: string;
    doctor_id?: string;
    target?: string;
  };
}

export interface AIChatRequest {
  message: string;
  conversation_id?: string;
  language?: 'ta' | 'en' | 'auto';
  patient_id?: string;
  village_id?: string;
  location_context?: string;
  user_role?: string;
}

export interface AIChatResponse {
  conversation_id: string;
  response_text: string;
  language: string;
  intent: string;
  tools_called: string[];
  cards: AIChatCard[];
  rag_sources: Array<{
    document: string;
    section: string;
    content: string;
    score: number;
  }>;
  action_taken?: string;
  disclaimer: string;
}

export interface AIHealthResponse {
  status: string;
  service: string;
  tools_count: number;
  rag_documents_indexed: number;
  llm_provider: string;
  voice_provider: string;
}

export interface VoiceTranscribeResponse {
  transcribed_text: string;
  detected_language: string;
  confidence: number;
  provider: string;
}

export interface VoiceSynthesizeResponse {
  audio_base64?: string;
  audio_url?: string;
  duration_seconds?: number;
  format: string;
  status: string;
  provider: string;
}

export const aiService = {
  /**
   * Send user message to CareBridge AI Assistant
   */
  async sendMessage(request: AIChatRequest): Promise<AIChatResponse> {
    return apiRequest<AIChatResponse>('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  /**
   * Transcribe base64 audio to text
   */
  async transcribeVoice(audioBase64: string, language: string = 'ta'): Promise<VoiceTranscribeResponse> {
    return apiRequest<VoiceTranscribeResponse>('/api/ai/voice/transcribe', {
      method: 'POST',
      body: JSON.stringify({
        audio_base64: audioBase64,
        audio_format: 'wav',
        language,
      }),
    });
  },

  /**
   * Synthesize text to spoken audio
   */
  async synthesizeVoice(text: string, language: string = 'ta'): Promise<VoiceSynthesizeResponse> {
    return apiRequest<VoiceSynthesizeResponse>('/api/ai/voice/synthesize', {
      method: 'POST',
      body: JSON.stringify({
        text,
        language,
        voice_gender: 'female',
      }),
    });
  },

  /**
   * Check AI subsystem health
   */
  async getHealth(): Promise<AIHealthResponse> {
    return apiRequest<AIHealthResponse>('/api/ai/health', {
      method: 'GET',
    });
  },

  /**
   * Submit satisfaction feedback
   */
  async submitFeedback(conversationId: string, rating: number, feedbackText?: string): Promise<any> {
    return apiRequest('/api/ai/feedback', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        rating,
        feedback_text: feedbackText,
      }),
    });
  },
};
