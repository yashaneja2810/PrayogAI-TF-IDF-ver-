import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Bot, Zap, MessageSquare, Plus, ArrowRight, FileText, Search, Code2, ArrowUpRight } from 'lucide-react';

interface DashboardStats {
  totalBots: number;
}

const Dashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats>({ totalBots: 0 });

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const botsResponse = await api.get('/api/bots');
        setStats({ totalBots: botsResponse.data.length });
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  return (
    <div className="p-8 max-w-5xl fade-in">
      {/* Welcome banner */}
      <div className="bg-gray-900 rounded-xl p-8 mb-8 relative overflow-hidden">
        <div className="absolute right-8 top-1/2 -translate-y-1/2 opacity-[0.05]">
          <Zap className="w-40 h-40" strokeWidth={1} />
        </div>
        <div className="relative">
          <h1 className="text-xl font-semibold text-white mb-1.5">Welcome to PrayogAI</h1>
          <p className="text-sm text-gray-400 mb-6 max-w-md">
            Build, deploy, and manage intelligent AI chatbots powered by your own documents.
          </p>
          <Link to="/create-bot" className="inline-flex items-center gap-2 px-4 py-2 bg-white text-gray-900 text-[13px] font-medium rounded-lg hover:bg-gray-100 transition-colors">
            <Plus className="w-4 h-4" />
            Create Your First Bot
          </Link>
        </div>
      </div>

      {/* Stats + Tech in a row */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-3">Total Bots</div>
          <div className="flex items-end justify-between">
            <span className="text-4xl font-semibold text-gray-900 tabular-nums">{isLoading ? '–' : stats.totalBots}</span>
            <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center">
              <Bot className="w-[18px] h-[18px] text-gray-500" />
            </div>
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-3">AI Engine</div>
          <div className="flex items-end justify-between">
            <div>
              <span className="text-lg font-semibold text-gray-900">Google Gemini</span>
              <p className="text-[11px] text-gray-400 mt-0.5">Language model</p>
            </div>
            <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center">
              <Zap className="w-[18px] h-[18px] text-gray-500" />
            </div>
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-3">Vector Store</div>
          <div className="flex items-end justify-between">
            <div>
              <span className="text-lg font-semibold text-gray-900">Qdrant Cloud</span>
              <p className="text-[11px] text-gray-400 mt-0.5">Semantic search</p>
            </div>
            <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-[18px] h-[18px] text-gray-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Two-column: Capabilities + Quick Actions */}
      <div className="grid grid-cols-5 gap-4">
        {/* Capabilities — spans 3 cols */}
        <div className="col-span-3 bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-[15px] font-semibold text-gray-900 mb-4">Platform Capabilities</h2>
          <div className="space-y-2">
            {[
              { icon: FileText, title: 'Document Processing', desc: 'Upload PDFs, DOCX, TXT to train your bot' },
              { icon: Search, title: 'Semantic Search', desc: 'AI-powered context retrieval for accurate answers' },
              { icon: Code2, title: 'Widget Integration', desc: 'Embed with a single script tag on any website' },
              { icon: Zap, title: 'Instant Deployment', desc: 'Go live in minutes — no coding required' },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group">
                <div className="w-8 h-8 bg-gray-100 rounded-md flex items-center justify-center flex-shrink-0 group-hover:bg-gray-200 transition-colors">
                  <Icon className="w-4 h-4 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-[13px] font-medium text-gray-900">{title}</span>
                  <span className="text-[12px] text-gray-400 ml-2">{desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions — spans 2 cols */}
        <div className="col-span-2 bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-[15px] font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <Link to="/create-bot" className="group flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="w-8 h-8 bg-gray-900 rounded-md flex items-center justify-center">
                <Plus className="w-4 h-4 text-white" />
              </div>
              <span className="text-[13px] font-medium text-gray-900 flex-1">Create New Bot</span>
              <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors" />
            </Link>
            <Link to="/bots" className="group flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="w-8 h-8 bg-gray-100 rounded-md flex items-center justify-center">
                <Bot className="w-4 h-4 text-gray-500" />
              </div>
              <span className="text-[13px] font-medium text-gray-900 flex-1">Manage Bots</span>
              <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors" />
            </Link>
          </div>

          <div className="mt-6 pt-5 border-t border-gray-100">
            <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-3">System Status</div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
              <span className="text-[12px] text-gray-600">All services operational</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;