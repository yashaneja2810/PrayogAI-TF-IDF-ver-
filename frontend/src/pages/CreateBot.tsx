import React, { useState, useCallback } from "react";
import { Upload, FileText, Loader2, CheckCircle2, XCircle, AlertCircle, Trash2, Bot, ArrowRight, Globe, Link2, Lock, ShieldCheck, Eye, EyeOff } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ChatWidget } from "../components/ChatWidget";
import { createBot, createDynamicBot } from "../lib/botApi";
import { useAuth } from "../context/AuthContext";
import { motion, AnimatePresence } from 'framer-motion';

type BotMode = 'static' | 'dynamic';
type AccessMode = 'public' | 'authenticated';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  status: "uploading" | "processing" | "completed" | "error";
  progress: number;
  file: File;
}

export const CreateBot: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  // Shared state
  const [mode, setMode] = useState<BotMode>('static');
  const [companyName, setCompanyName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [botCreated, setBotCreated] = useState(false);
  const [createdBotId, setCreatedBotId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Static bot state
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Dynamic bot state
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [scrapeStats, setScrapeStats] = useState<{ pages: number; chunks: number } | null>(null);
  const [accessMode, setAccessMode] = useState<AccessMode>('public');
  const [loginUrl, setLoginUrl] = useState("");
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginRole, setLoginRole] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [acceptedWarning, setAcceptedWarning] = useState(false);

  React.useEffect(() => {
    if (!isAuthenticated) navigate("/login");
  }, [isAuthenticated, navigate]);

  // Reset when switching modes
  const switchMode = (newMode: BotMode) => {
    setMode(newMode);
    setError(null);
    setBotCreated(false);
    setCreatedBotId(null);
    setScrapeStats(null);
    setFiles([]);
    setCompanyName("");
    setWebsiteUrl("");
    setAccessMode('public');
    setLoginUrl("");
    setLoginUsername("");
    setLoginPassword("");
    setLoginRole("");
    setAcceptedWarning(false);
  };

  // ── Static bot handlers ──────────────────────────────
  const handleFiles = useCallback((selectedFiles: File[]) => {
    const pdfFiles = selectedFiles.filter((file) => file.type === "application/pdf");
    pdfFiles.forEach((file) => {
      const fileId = Date.now().toString() + Math.random();
      setFiles((prev) => [...prev, { id: fileId, name: file.name, size: file.size, status: "completed", progress: 100, file }]);
    });
  }, []);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => { setIsDragging(false); };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files) handleFiles(Array.from(e.dataTransfer.files));
  };
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) handleFiles(Array.from(e.target.files));
  };
  const removeFile = (fileId: string) => { setFiles((f) => f.filter((file) => file.id !== fileId)); };

  const handleCreateStaticBot = async () => {
    if (!companyName) { setError("Please enter a bot name"); return; }
    if (files.length === 0) { setError("Please upload at least one PDF file"); return; }
    setError(null); setIsCreating(true);
    try {
      const formData = new FormData();
      formData.append("company_name", companyName);
      files.forEach((file) => formData.append("files", file.file));
      const response = await createBot(formData);
      setCreatedBotId(response.bot_id); setBotCreated(true);
    } catch (err) { setError("Failed to create bot. Please try again."); }
    finally { setIsCreating(false); }
  };

  // ── Dynamic bot handlers ─────────────────────────────
  const handleCreateDynamicBot = async () => {
    if (!companyName) { setError("Please enter a bot name"); return; }
    if (!websiteUrl) { setError("Please enter a website URL"); return; }
    try {
      const url = websiteUrl.startsWith('http') ? websiteUrl : `https://${websiteUrl}`;
      new URL(url);
    } catch { setError("Please enter a valid URL (e.g. https://example.com)"); return; }

    if (accessMode === 'authenticated') {
      if (!loginUrl) { setError("Please enter the login page URL"); return; }
      if (!loginUsername) { setError("Please enter the login username/email"); return; }
      if (!loginPassword) { setError("Please enter the login password"); return; }
      if (!acceptedWarning) { setError("Please acknowledge the security notice to proceed"); return; }
    }

    setError(null); setIsCreating(true);
    try {
      const response = await createDynamicBot(
        companyName,
        websiteUrl,
        accessMode === 'authenticated' ? loginUrl : undefined,
        accessMode === 'authenticated' ? loginUsername : undefined,
        accessMode === 'authenticated' ? loginPassword : undefined,
        accessMode === 'authenticated' && loginRole ? loginRole : undefined,
      );
      setCreatedBotId(response.bot_id);
      setScrapeStats({ pages: response.pages_scraped, chunks: response.total_chunks });
      setBotCreated(true);
      // Clear credentials from memory immediately after use
      setLoginPassword("");
      setLoginUsername("");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to scrape website. Please try again.";
      setError(msg);
    } finally { setIsCreating(false); }
  };

  return (
    <div className="p-8 max-w-5xl fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-gray-900">Create a New Bot</h1>
        <p className="text-[13px] text-gray-400 mt-0.5">Choose how to train your AI chatbot</p>
      </div>

      {/* Mode Tabs */}
      <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-lg w-fit mb-8">
        <button
          onClick={() => switchMode('static')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-[13px] font-medium transition-all duration-150 ${
            mode === 'static'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="w-4 h-4" />
          Static Bot
        </button>
        <button
          onClick={() => switchMode('dynamic')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-[13px] font-medium transition-all duration-150 ${
            mode === 'dynamic'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Globe className="w-4 h-4" />
          Dynamic Bot
        </button>
      </div>

      {/* Mode Description */}
      <div className="mb-6">
        {mode === 'static' ? (
          <div className="flex items-start gap-3 p-4 bg-gray-50 border border-gray-100 rounded-lg">
            <FileText className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-[13px] font-medium text-gray-700">Upload PDF documents</p>
              <p className="text-[12px] text-gray-400 mt-0.5">Train your bot on specific documents. Best for manuals, guides, and knowledge bases.</p>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3 p-4 bg-gray-50 border border-gray-100 rounded-lg">
            <Globe className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-[13px] font-medium text-gray-700">Scrape a website</p>
              <p className="text-[12px] text-gray-400 mt-0.5">Provide your website URL and we'll crawl pages, extract content, and build a chatbot from it automatically.</p>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="space-y-6">
        <AnimatePresence mode="wait">
          {mode === 'static' ? (
            <motion.div key="static" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.15 }}>
              <div className="bg-white border border-gray-200 rounded-xl p-6">
                {!botCreated ? (
                  <div className="grid grid-cols-2 gap-8">
                    {/* Left — inputs */}
                    <div className="space-y-5">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-6 h-6 bg-gray-900 rounded-full flex items-center justify-center text-white text-[11px] font-semibold">1</div>
                        <span className="text-[13px] font-medium text-gray-900">Bot Details</span>
                      </div>
                      <div>
                        <label htmlFor="staticBotName" className="block text-[13px] font-medium text-gray-700 mb-1.5">Bot Name</label>
                        <input type="text" id="staticBotName" value={companyName} onChange={(e) => setCompanyName(e.target.value)}
                          placeholder="e.g. Customer Support Bot" className="input-field" />
                      </div>
                      {files.length > 0 && (
                        <div className="space-y-1.5">
                          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">{files.length} file{files.length !== 1 ? 's' : ''} selected</span>
                          {files.map((file) => (
                            <div key={file.id} className="flex items-center justify-between py-2 px-3 bg-gray-50 border border-gray-100 rounded-lg">
                              <div className="flex items-center gap-2 min-w-0">
                                <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                                <span className="text-[13px] text-gray-700 truncate">{file.name}</span>
                                <span className="text-[11px] text-gray-400 flex-shrink-0">{(file.size / 1024 / 1024).toFixed(1)} MB</span>
                              </div>
                              <div className="flex items-center gap-2 ml-2">
                                {file.status === "completed" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                                {file.status === "error" && <XCircle className="w-3.5 h-3.5 text-red-500" />}
                                <button onClick={() => removeFile(file.id)} className="p-0.5 rounded hover:bg-gray-200 transition-colors">
                                  <Trash2 className="w-3 h-3 text-gray-400" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      {error && <ErrorBanner message={error} />}
                      <button onClick={handleCreateStaticBot} disabled={isCreating} className="btn-primary w-full">
                        {isCreating ? <><Loader2 className="w-4 h-4 animate-spin" />Creating…</> : <>Create Bot<ArrowRight className="w-4 h-4" /></>}
                      </button>
                    </div>
                    {/* Right — upload zone */}
                    <div>
                      <div className="flex items-center gap-2 mb-4">
                        <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 text-[11px] font-semibold">2</div>
                        <span className="text-[13px] font-medium text-gray-900">Upload Documents</span>
                      </div>
                      <div onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
                        className={`border-2 border-dashed rounded-xl p-10 text-center transition-all duration-150 h-[calc(100%-40px)] flex flex-col items-center justify-center ${
                          isDragging ? "border-gray-900 bg-gray-50" : "border-gray-200 hover:border-gray-300 bg-gray-50/50"
                        }`}>
                        <input type="file" id="file-upload" className="hidden" onChange={handleFileSelect} multiple accept=".pdf" />
                        <div className="w-12 h-12 bg-white border border-gray-200 rounded-xl flex items-center justify-center mb-4 shadow-sm">
                          <Upload className="w-5 h-5 text-gray-400" />
                        </div>
                        <label htmlFor="file-upload" className="text-[13px] text-gray-900 font-medium cursor-pointer hover:underline">Choose PDF files</label>
                        <p className="text-[12px] text-gray-400 mt-1">or drag and drop here</p>
                        <p className="text-[11px] text-gray-300 mt-3">Max 10MB per file</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <SuccessState botName={companyName} />
                )}
              </div>
            </motion.div>
          ) : (
            <motion.div key="dynamic" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.15 }}>
              <div className="bg-white border border-gray-200 rounded-xl p-6">
                {!botCreated ? (
                  <div className="space-y-6">
                    {/* Top row: Bot name + URL */}
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <label htmlFor="dynamicBotName" className="block text-[13px] font-medium text-gray-700 mb-1.5">Bot Name</label>
                        <input type="text" id="dynamicBotName" value={companyName} onChange={(e) => setCompanyName(e.target.value)}
                          placeholder="e.g. My Company Bot" className="input-field" />
                      </div>
                      <div>
                        <label htmlFor="websiteUrl" className="block text-[13px] font-medium text-gray-700 mb-1.5">Website URL</label>
                        <div className="relative">
                          <Link2 className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                          <input type="url" id="websiteUrl" value={websiteUrl} onChange={(e) => setWebsiteUrl(e.target.value)}
                            placeholder="https://example.com" className="input-field pl-9" />
                        </div>
                      </div>
                    </div>

                    {/* Access Mode Toggle */}
                    <div>
                      <label className="block text-[13px] font-medium text-gray-700 mb-2">Website Access</label>
                      <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-lg w-fit">
                        <button
                          onClick={() => { setAccessMode('public'); setAcceptedWarning(false); }}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium transition-all duration-150 ${
                            accessMode === 'public' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                          }`}
                        >
                          <Globe className="w-3.5 h-3.5" />
                          Public Website
                        </button>
                        <button
                          onClick={() => setAccessMode('authenticated')}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium transition-all duration-150 ${
                            accessMode === 'authenticated' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                          }`}
                        >
                          <Lock className="w-3.5 h-3.5" />
                          Requires Login
                        </button>
                      </div>
                    </div>

                    {/* Authenticated fields */}
                    <AnimatePresence>
                      {accessMode === 'authenticated' && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="space-y-4">
                            {/* Security Notice */}
                            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                              <div className="flex items-start gap-3">
                                <ShieldCheck className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="text-[13px] font-medium text-amber-800">Security Notice</p>
                                  <p className="text-[12px] text-amber-700 mt-1 leading-relaxed">
                                    Your credentials are used <strong>only once</strong> to log into the website during scraping.
                                    They are processed entirely in-memory and are <strong>never stored, logged, or visible to our servers</strong>.
                                    Credentials are immediately discarded after the scraping session ends.
                                  </p>
                                  <label className="flex items-center gap-2 mt-3 cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={acceptedWarning}
                                      onChange={(e) => setAcceptedWarning(e.target.checked)}
                                      className="w-3.5 h-3.5 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                                    />
                                    <span className="text-[12px] text-amber-800 font-medium">I understand and wish to proceed</span>
                                  </label>
                                </div>
                              </div>
                            </div>

                            {/* Login fields */}
                            <div className="grid grid-cols-1 gap-4">
                              <div>
                                <label htmlFor="loginUrl" className="block text-[13px] font-medium text-gray-700 mb-1.5">Login Page URL</label>
                                <div className="relative">
                                  <Link2 className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                  <input type="url" id="loginUrl" value={loginUrl} onChange={(e) => setLoginUrl(e.target.value)}
                                    placeholder="https://example.com/login" className="input-field pl-9" />
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <label htmlFor="loginUsername" className="block text-[13px] font-medium text-gray-700 mb-1.5">Username / Email</label>
                                  <input type="text" id="loginUsername" value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)}
                                    placeholder="user@example.com" className="input-field" autoComplete="off" />
                                </div>
                                <div>
                                  <label htmlFor="loginPassword" className="block text-[13px] font-medium text-gray-700 mb-1.5">Password</label>
                                  <div className="relative">
                                    <input
                                      type={showPassword ? "text" : "password"}
                                      id="loginPassword"
                                      value={loginPassword}
                                      onChange={(e) => setLoginPassword(e.target.value)}
                                      placeholder="••••••••"
                                      className="input-field pr-10"
                                      autoComplete="off"
                                    />
                                    <button
                                      type="button"
                                      onClick={() => setShowPassword(!showPassword)}
                                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                                    >
                                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                    </button>
                                  </div>
                                </div>
                              </div>
                              <div>
                                <label htmlFor="loginRole" className="block text-[13px] font-medium text-gray-700 mb-1.5">
                                  User Role <span className="text-gray-400 font-normal">(optional)</span>
                                </label>
                                <input type="text" id="loginRole" value={loginRole} onChange={(e) => setLoginRole(e.target.value)}
                                  placeholder="e.g. Student, Employee, Admin" className="input-field" autoComplete="off" />
                                <p className="text-[11px] text-gray-400 mt-1">If the login page has role cards or tabs, enter your role here</p>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {error && <ErrorBanner message={error} />}

                    <button onClick={handleCreateDynamicBot} disabled={isCreating} className="btn-primary w-full">
                      {isCreating ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <div>
                            <span>{accessMode === 'authenticated' ? 'Logging in & scraping…' : 'Scraping website…'}</span>
                            <span className="ml-1 text-gray-400 text-[11px]">this may take a minute</span>
                          </div>
                        </div>
                      ) : (
                        <>
                          {accessMode === 'authenticated' ? <Lock className="w-4 h-4" /> : <Globe className="w-4 h-4" />}
                          {accessMode === 'authenticated' ? 'Login & Scrape' : 'Scrape & Create Bot'}
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <SuccessState botName={companyName} />
                    {scrapeStats && (
                      <div className="flex items-center justify-center gap-6 pt-2">
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-gray-900">{scrapeStats.pages}</div>
                          <div className="text-[11px] text-gray-400 mt-0.5">Pages scraped</div>
                        </div>
                        <div className="w-px h-8 bg-gray-200"></div>
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-gray-900">{scrapeStats.chunks}</div>
                          <div className="text-[11px] text-gray-400 mt-0.5">Text chunks</div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat preview */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          {createdBotId ? (
            <>
              <div className="px-5 py-4 border-b border-gray-200">
                <h3 className="text-[15px] font-semibold text-gray-900">Test: {companyName}</h3>
                <p className="text-[12px] text-gray-400 mt-0.5">Start a conversation</p>
              </div>
              <ChatWidget botId={createdBotId} botName={companyName} companyName={companyName} className="h-[350px] border-none rounded-none" />
            </>
          ) : (
            <div className="h-64 flex items-center justify-center">
              <div className="text-center">
                <Bot className="w-8 h-8 mx-auto mb-2 text-gray-200" />
                <p className="text-[13px] text-gray-400">Chat preview appears after bot creation</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Shared components ────────────────────────────────
const SuccessState: React.FC<{ botName: string }> = ({ botName }) => (
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-10">
    <div className="w-14 h-14 bg-gray-900 rounded-full mx-auto flex items-center justify-center mb-4">
      <CheckCircle2 className="w-7 h-7 text-white" />
    </div>
    <h2 className="text-lg font-semibold text-gray-900 mb-1">Bot created successfully</h2>
    <p className="text-[13px] text-gray-400">{botName} is ready. Try it below.</p>
  </motion.div>
);

const ErrorBanner: React.FC<{ message: string }> = ({ message }) => (
  <div className="flex items-center gap-2 p-2.5 bg-red-50 border border-red-200 rounded-lg">
    <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
    <p className="text-[13px] text-red-600">{message}</p>
  </div>
);

export default CreateBot;