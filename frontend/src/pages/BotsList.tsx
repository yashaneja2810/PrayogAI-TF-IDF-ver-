import React, { useEffect, useState } from 'react';
import { FileText, Loader2, Search, Eye, Plus, Code2, Trash2, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ChatWidget } from '../components/ChatWidget';
import { Modal } from '../components/Modal';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { deleteBot } from '../lib/botApi';

interface Bot {
  id: string;
  bot_id: string;
  name: string;
  created_at: string;
  status: 'ready' | 'processing' | 'error';
  user_id: string;
}

interface BotDocument {
  id: string;
  bot_id: string;
  filename: string;
  file_size: number;
  created_at: string;
}

export const BotsList: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const [bots, setBots] = useState<Bot[]>([]);
  const [documents, setDocuments] = useState<Record<string, BotDocument[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [widgetModalBot, setWidgetModalBot] = useState<Bot | null>(null);
  const [deletingBot, setDeletingBot] = useState<string | null>(null);
  const [botToDelete, setBotToDelete] = useState<Bot | null>(null);

  const handleClickOutside = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) { setSelectedBot(null); setWidgetModalBot(null); }
  };

  const handleDeleteBot = async (bot: Bot) => { setBotToDelete(bot); };

  const confirmDelete = async () => {
    if (!botToDelete) return;
    try {
      setDeletingBot(botToDelete.bot_id);
      await deleteBot(botToDelete.bot_id);
      setBots(bots => bots.filter(b => b.bot_id !== botToDelete.bot_id));
      setBotToDelete(null);
    } catch (err) {
      setError('Failed to delete bot. Please try again.');
    } finally { setDeletingBot(null); }
  };

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      setBots([]); setDocuments({}); setSearchQuery(''); setSelectedBot(null); setWidgetModalBot(null); setBotToDelete(null);
    } else { fetchBots(); }
    return () => { setBots([]); setDocuments({}); setSearchQuery(''); setSelectedBot(null); setWidgetModalBot(null); setBotToDelete(null); };
  }, [isAuthenticated, user, navigate]);

  const fetchBots = async () => {
    setBots([]); setDocuments({}); setSearchQuery(''); setSelectedBot(null); setWidgetModalBot(null); setBotToDelete(null);
    setIsLoading(true); setError(null);
    try {
      const response = await api.get<Bot[]>('/api/bots');
      const botsData = response.data;
      if (Array.isArray(botsData)) {
        setBots(botsData);
        setIsLoading(false);
        if (botsData.length > 0) botsData.forEach(bot => fetchBotDocuments(bot.bot_id));
      } else { setError('Invalid response format from server'); }
    } catch (error: any) {
      const errorMessage = error.response?.status === 401 ? 'Session expired. Please log in again.' : 'Failed to fetch bots. Please try again later.';
      console.error('Error fetching bots:', error);
      setError(errorMessage);
      if (error.response?.status === 401) { setBots([]); setDocuments({}); }
      setIsLoading(false);
    }
  };

  const fetchBotDocuments = async (botId: string) => {
    if (documents[botId]) return;
    try {
      const docsResponse = await api.get(`/api/bots/${botId}/documents`);
      setDocuments(prev => ({ ...prev, [botId]: docsResponse.data.documents || [] }));
    } catch (error) {
      console.error(`Error fetching documents for bot ${botId}:`, error);
      setDocuments(prev => ({ ...prev, [botId]: [] }));
    }
  };

  const filteredBots = bots.filter(bot => bot.name.toLowerCase().includes(searchQuery.toLowerCase()));

  const getStatusBadge = (status: Bot['status']) => {
    const config = {
      ready: { bg: 'bg-emerald-50', text: 'text-emerald-600', border: 'border-emerald-200', dot: 'bg-emerald-500', label: 'Ready' },
      processing: { bg: 'bg-amber-50', text: 'text-amber-600', border: 'border-amber-200', dot: '', label: 'Processing' },
      error: { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200', dot: 'bg-red-500', label: 'Error' },
    }[status] || { bg: 'bg-gray-50', text: 'text-gray-500', border: 'border-gray-200', dot: '', label: 'Unknown' };

    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium ${config.bg} ${config.text} border ${config.border}`}>
        {status === 'processing' ? <Loader2 className="w-3 h-3 animate-spin" /> : config.dot && <div className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />}
        {config.label}
      </span>
    );
  };

  const formatDate = (dateString: string) => new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center gap-2 text-gray-400"><Loader2 className="w-4 h-4 animate-spin" /><span className="text-[13px]">Loading…</span></div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl fade-in">
      {/* Header row */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">My Bots</h1>
          <p className="text-[13px] text-gray-400 mt-0.5">{filteredBots.length} bot{filteredBots.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          {error && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-50 border border-red-200">
              <span className="text-[12px] text-red-600">{error}</span>
            </div>
          )}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search…" className="w-48 pl-8 pr-3 py-[7px] bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 text-[13px] placeholder-gray-400 transition-all" />
          </div>
          <button onClick={() => navigate('/create-bot')} className="btn-primary">
            <Plus className="w-4 h-4" />New Bot
          </button>
        </div>
      </div>

      {/* Table-style list */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-[1fr_120px_160px_140px] gap-4 px-5 py-3 bg-gray-50 border-b border-gray-200">
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Bot</span>
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Status</span>
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Created</span>
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider text-right">Actions</span>
        </div>

        {/* Rows */}
        {filteredBots.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <p className="text-[13px] text-gray-400">No bots found</p>
          </div>
        ) : (
          filteredBots.map((bot, idx) => {
            const docs = documents[bot.bot_id];
            const realDocs = docs ? docs.filter(doc => !/^document_\d+\.txt$/.test(doc.filename)) : [];

            return (
              <div key={bot.bot_id} className={`grid grid-cols-[1fr_120px_160px_140px] gap-4 px-5 py-4 items-center hover:bg-gray-50 transition-colors ${idx < filteredBots.length - 1 ? 'border-b border-gray-100' : ''}`}>
                {/* Bot info */}
                <div className="min-w-0">
                  <div className="text-[14px] font-medium text-gray-900 truncate">{bot.name}</div>
                  {docs === undefined ? (
                    <div className="flex items-center gap-1 mt-1"><Loader2 className="w-3 h-3 animate-spin text-gray-300" /><span className="text-[11px] text-gray-400">Loading docs…</span></div>
                  ) : realDocs.length > 0 ? (
                    <div className="flex items-center gap-1 mt-1"><FileText className="w-3 h-3 text-gray-400" /><span className="text-[11px] text-gray-400">{realDocs.length} document{realDocs.length !== 1 ? 's' : ''}</span></div>
                  ) : null}
                </div>

                {/* Status */}
                <div>{getStatusBadge(bot.status)}</div>

                {/* Date */}
                <div className="text-[12px] text-gray-500">{formatDate(bot.created_at)}</div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 justify-end">
                  <button onClick={() => setSelectedBot(bot)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors" title="Test">
                    <Eye className="w-4 h-4" />
                  </button>
                  <button onClick={() => setWidgetModalBot(bot)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors" title="Widget code">
                    <Code2 className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDeleteBot(bot)} disabled={!!deletingBot}
                    className={`p-1.5 rounded-md transition-colors ${deletingBot === bot.bot_id ? 'text-red-300' : 'text-gray-400 hover:text-red-600 hover:bg-red-50'}`} title="Delete">
                    {deletingBot === bot.bot_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Chat Test Modal */}
      {selectedBot && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50" onClick={handleClickOutside}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
              <div>
                <h3 className="text-[15px] font-semibold text-gray-900">Test: {selectedBot.name}</h3>
                <p className="text-[12px] text-gray-400 mt-0.5">Chat with your AI assistant</p>
              </div>
              <button onClick={() => setSelectedBot(null)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <ChatWidget botId={selectedBot.bot_id} botName={selectedBot.name} companyName={selectedBot.name} />
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      <Modal isOpen={!!botToDelete} onClose={() => setBotToDelete(null)} title="Delete Bot">
        {botToDelete && (
          <div className="space-y-5">
            <p className="text-[13px] text-gray-600">Are you sure you want to delete <span className="font-semibold text-gray-900">{botToDelete.name}</span>? This cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setBotToDelete(null)} className="btn-secondary text-[12px]">Cancel</button>
              <button onClick={confirmDelete} disabled={!!deletingBot}
                className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] font-medium text-white transition-colors ${deletingBot ? 'bg-red-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700'}`}>
                {deletingBot ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Deleting…</> : <><Trash2 className="w-3.5 h-3.5" />Delete</>}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Widget Modal */}
      <Modal isOpen={!!widgetModalBot} onClose={() => setWidgetModalBot(null)} title="Embed Widget">
        {widgetModalBot && (
          <div className="space-y-4">
            <p className="text-[13px] text-gray-600">Add this to your website's <code className="text-[11px] bg-gray-100 px-1 py-0.5 rounded">&lt;body&gt;</code> for <span className="font-semibold">{widgetModalBot.name}</span>:</p>
            <pre className="bg-gray-900 text-gray-300 text-[12px] p-4 rounded-lg overflow-x-auto select-all font-mono leading-relaxed">
              {`<script 
  src="http://localhost:5173/widget/widget.js"
  data-bot-id="${widgetModalBot.bot_id}"
  data-company-name="${widgetModalBot.name}"
  data-color="#2563eb">
</script>`}
            </pre>
            <div className="text-[11px] text-gray-400 space-y-1">
              <p><span className="font-medium text-gray-500">data-company-name</span> — Header title</p>
              <p><span className="font-medium text-gray-500">data-color</span> — Primary color</p>
              <p className="text-gray-400 mt-2">Update <code className="bg-gray-100 px-1 rounded">src</code> URL for production.</p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default BotsList;