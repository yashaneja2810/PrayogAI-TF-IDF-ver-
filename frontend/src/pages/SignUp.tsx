import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, CheckCircle2, Mail, Lock } from 'lucide-react';
import { signup } from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';

export const SignUp: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showVerificationMessage, setShowVerificationMessage] = useState(false);
    const navigate = useNavigate();

    const validateForm = () => {
        if (!email || !password || !confirmPassword) {
            setError('All fields are required');
            return false;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            setError('Please enter a valid email address');
            return false;
        }
        if (password.length < 8) {
            setError('Password must be at least 8 characters long');
            return false;
        }
        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return false;
        }
        return true;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!validateForm()) return;
        setIsLoading(true);

        try {
            await signup(email, password);
            setShowVerificationMessage(true);
            setTimeout(() => { navigate('/login'); }, 3000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create account. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-6">
            <div className="w-full max-w-[400px]">
                {/* Branding */}
                <div className="text-center mb-10">
                    <div className="inline-flex items-center justify-center w-12 h-12 bg-white rounded-xl mb-5">
                        <svg className="w-6 h-6 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <h1 className="text-2xl font-semibold text-white mb-1">Create your account</h1>
                    <p className="text-sm text-gray-400">Start building AI chatbots today</p>
                </div>

                {/* Form card */}
                <AnimatePresence mode="wait">
                    {!showVerificationMessage ? (
                        <motion.div
                            key="form"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.15 }}
                            className="bg-white rounded-xl p-7 shadow-2xl shadow-black/20"
                        >
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div>
                                    <label htmlFor="email" className="block text-[13px] font-medium text-gray-700 mb-1.5">Email</label>
                                    <div className="relative">
                                        <Mail className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                        <input id="email" name="email" type="email" required autoComplete="email"
                                            className="input-field pl-9" placeholder="you@company.com"
                                            value={email} onChange={(e) => setEmail(e.target.value)} />
                                    </div>
                                </div>

                                <div>
                                    <label htmlFor="password" className="block text-[13px] font-medium text-gray-700 mb-1.5">Password</label>
                                    <div className="relative">
                                        <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                        <input id="password" name="password" type={showPassword ? 'text' : 'password'} required
                                            autoComplete="new-password" className="input-field pl-9 pr-10" placeholder="••••••••"
                                            value={password} onChange={(e) => setPassword(e.target.value)} />
                                        <button type="button" onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                        </button>
                                    </div>
                                    <p className="text-[11px] text-gray-400 mt-1">Min. 8 characters</p>
                                </div>

                                <div>
                                    <label htmlFor="confirmPassword" className="block text-[13px] font-medium text-gray-700 mb-1.5">Confirm Password</label>
                                    <div className="relative">
                                        <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                        <input id="confirmPassword" name="confirmPassword" type={showConfirmPassword ? 'text' : 'password'}
                                            required autoComplete="new-password" className="input-field pl-9 pr-10" placeholder="••••••••"
                                            value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                                        <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                                            {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                        </button>
                                    </div>
                                </div>

                                {error && (
                                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                        className="flex items-center gap-2 p-2.5 bg-red-50 border border-red-200 rounded-lg">
                                        <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <span className="text-[13px] text-red-600">{error}</span>
                                    </motion.div>
                                )}

                                <button type="submit" disabled={isLoading} className="btn-primary w-full mt-1">
                                    {isLoading ? (
                                        <>
                                            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                            </svg>
                                            Creating account…
                                        </>
                                    ) : 'Create account'}
                                </button>
                            </form>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="verify"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-white rounded-xl p-10 shadow-2xl shadow-black/20 text-center"
                        >
                            <div className="w-14 h-14 bg-gray-900 rounded-full mx-auto flex items-center justify-center mb-5">
                                <CheckCircle2 className="w-7 h-7 text-white" />
                            </div>
                            <h2 className="text-lg font-semibold text-gray-900 mb-2">Check your email</h2>
                            <p className="text-[13px] text-gray-500 mb-1">We sent a verification link to</p>
                            <p className="text-[13px] font-semibold text-gray-900 mb-4">{email}</p>
                            <p className="text-[11px] text-gray-400">Redirecting to login…</p>
                            <div className="mt-5">
                                <div className="w-28 h-1 bg-gray-100 rounded-full mx-auto overflow-hidden">
                                    <motion.div initial={{ width: 0 }} animate={{ width: "100%" }}
                                        transition={{ duration: 3, ease: "linear" }} className="h-full bg-gray-900 rounded-full" />
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <p className="mt-6 text-center text-[13px] text-gray-500">
                    Already have an account?{' '}
                    <a href="/login" className="text-white hover:underline font-medium">Sign in</a>
                </p>
            </div>
        </div>
    );
};
