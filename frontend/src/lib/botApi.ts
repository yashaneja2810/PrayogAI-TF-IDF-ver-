import { api } from './api';

export interface Bot {
    id: string;
    name: string;
    created_at: string;
    user_id: string;
}

export interface CreateBotResponse {
    bot_id: string;
    widget_code: string;
    message: string;
}

export interface CreateDynamicBotResponse {
    bot_id: string;
    widget_code: string;
    message: string;
    pages_scraped: number;
    total_chunks: number;
}

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export const createBot = async (formData: FormData): Promise<CreateBotResponse> => {
    const response = await api.post('/api/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const createDynamicBot = async (
    companyName: string,
    websiteUrl: string,
    loginUrl?: string,
    loginUsername?: string,
    loginPassword?: string,
    loginRole?: string,
): Promise<CreateDynamicBotResponse> => {
    const payload: any = {
        company_name: companyName,
        website_url: websiteUrl,
    };
    if (loginUrl && loginUsername && loginPassword) {
        payload.login_url = loginUrl;
        payload.login_username = loginUsername;
        payload.login_password = loginPassword;
        if (loginRole) {
            payload.login_role = loginRole;
        }
    }
    const response = await api.post('/api/scrape', payload);
    return response.data;
};

export const sendChatMessage = async (botId: string, message: string) => {
    const response = await api.post('/api/chat', {
        bot_id: botId,
        query: message,
    });
    return response.data;
};

export const deleteBot = async (botId: string): Promise<void> => {
    await api.delete(`/api/bots/${botId}`);
};

