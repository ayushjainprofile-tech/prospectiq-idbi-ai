import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useRef, useEffect, KeyboardEvent } from "react";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  History,
  Star,
  Settings,
  Paperclip,
  Mic,
  ArrowUp,
  Sparkles,
  Plus,
  Upload,
  AudioLines,
  ShieldCheck
} from "lucide-react";
import mascot from "@/assets/mascot.png";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ProspectIQ — IDBI Bank" },
      { name: "description", content: "IDBI Bank AI Customer Acquisition" },
    ],
  }),
  component: Index,
});

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard" },
  { icon: MessageSquare, label: "AI Chats", active: true },
  { icon: FileText, label: "Documents" },
  { icon: History, label: "History" },
  { icon: Star, label: "Favorites" },
  { icon: Settings, label: "Settings" },
];

const quickActions = [
  { icon: Plus, label: "New Chat", color: "bg-brand-pink" },
  { icon: Upload, label: "Upload KYC", color: "bg-brand-yellow" },
  { icon: ShieldCheck, label: "Verify", color: "bg-brand-purple" },
  { icon: AudioLines, label: "Voice", color: "bg-brand-green" },
];

type Message = {
  role: 'user' | 'assistant';
  content: string;
  lead?: {
    name: string;
    product: string;
    income: string;
    score: number;
    tag: string;
  };
};

function Index() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Namaste! 🙏 I\'m ProspectIQ, IDBI Bank\'s AI assistant. How can I help you with your banking needs today?'
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [stage, setStage] = useState("identify");
  const [activeNav, setActiveNav] = useState("AI Chats");
  const [sessionId, setSessionId] = useState(() => Math.random().toString(36).substring(7));
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleNewChat = () => {
    setSessionId(Math.random().toString(36).substring(7));
    setStage("identify");
    setMessages([
      {
        role: 'assistant',
        content: 'Namaste! 🙏 Started a new session with ProspectIQ. How can I assist you with IDBI Bank services today?'
      }
    ]);
  };

  const handleQuickAction = (label: string) => {
    setActiveNav("AI Chats");
    if (label === "New Chat") {
      handleNewChat();
    } else if (label === "Upload KYC") {
      fileInputRef.current?.click();
    } else if (label === "Verify") {
      setMessages(prev => [
        ...prev,
        { role: 'user', content: '🔒 Initiate Identity & KYC Verification' },
        { 
          role: 'assistant', 
          content: '✅ Identity Verification Successful!\n\n• Aadhaar e-KYC: Verified\n• PAN Validation: Active\n• Credit Rating Check: Approved for IDBI Bank Pre-Approved Loans' 
        }
      ]);
    } else if (label === "Voice") {
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        try {
          const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
          const recognition = new SpeechRecognition();
          recognition.lang = 'en-IN';
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: '🎙️ Voice Assistant Active! Listening to your microphone... Please speak your query.' }
          ]);
          recognition.start();
          recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            sendMessage(transcript);
          };
          recognition.onerror = () => {
            setMessages(prev => [
              ...prev,
              { role: 'assistant', content: '🎙️ Microphone capture ready! Type your voice query or grant mic permissions.' }
            ]);
          };
        } catch (err) {
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: '🎙️ Voice Assistant Mode Enabled!' }
          ]);
        }
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: '🎙️ Voice Assistant Mode Enabled! (Type your spoken query in the input box).' }
        ]);
      }
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setMessages(prev => [
        ...prev,
        { role: 'user', content: `Uploaded document: ${file.name}` },
        { role: 'assistant', content: `📄 Received ${file.name}! Processing document for IDBI Bank KYC verification...` }
      ]);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;
    
    const newMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, newMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text
        })
      });
      
      const rawText = await res.text();
      let data;
      try {
        data = JSON.parse(rawText);
      } catch (e) {
        setMessages(prev => [...prev, { role: 'assistant', content: `Server Error: ${res.status} - ${rawText.substring(0, 100)}` }]);
        setIsLoading(false);
        return;
      }
      
      if (res.ok) {
        setStage(data.stage);
        const aiMsg: Message = { role: 'assistant', content: data.reply };
        if (data.lead_captured) {
          aiMsg.lead = data.lead_data;
        }
        setMessages(prev => [...prev, aiMsg]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.detail || 'Failed to get response'}` }]);
      }
    } catch (error: unknown) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Network/Backend Error: ${error instanceof Error ? error.message : String(error)}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="min-h-screen w-full bg-canvas p-3 text-ink font-sans">
      <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept="image/*,.pdf" />
      <div className="flex gap-3 h-[calc(100vh-1.5rem)]">
        {/* SIDEBAR */}
        <aside className="hidden lg:flex w-[18%] min-w-[220px] flex-col rounded-[28px] bg-sidebar p-5 text-sidebar-foreground">
          <div className="flex items-center gap-2.5 px-2 pb-6">
            <div className="grid h-9 w-9 place-items-center rounded-2xl bg-[#F5A623] text-ink">
              <Sparkles className="h-4 w-4" strokeWidth={2.5} />
            </div>
            <div className="text-[17px] font-bold tracking-tight text-white">ProspectIQ</div>
          </div>

          <nav className="flex flex-col gap-1">
            {navItems.map((item) => {
              const isActive = activeNav === item.label;
              return (
                <motion.button
                  key={item.label}
                  whileHover={{ x: 2 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setActiveNav(item.label);
                    if (item.label === "Dashboard") {
                      setMessages(prev => [
                        ...prev,
                        { role: 'assistant', content: '📊 Executive Analytics Overview:\n• Total Leads Today: 28\n• Conversion Rate: 64%\n• High-Priority Prospect Score Average: 82/99' }
                      ]);
                    } else if (item.label === "Documents") {
                      setMessages(prev => [
                        ...prev,
                        { role: 'assistant', content: '📁 Customer Documents Portal:\n1. Aadhaar_eKYC_Verified.pdf\n2. Income_Tax_Return_FY25.pdf\n3. IDBI_HomeLoan_Agreement_Draft.docx' }
                      ]);
                    } else if (item.label === "History") {
                      setMessages(prev => [
                        ...prev,
                        { role: 'assistant', content: '📜 Conversation History Log:\n• Session #9821: Home Loan Eligibility Check\n• Session #9744: Super Savings Account Opening' }
                      ]);
                    } else if (item.label === "Favorites") {
                      setMessages(prev => [
                        ...prev,
                        { role: 'assistant', content: '⭐ Starred Products:\n• IDBI Super Savings Account (High Return)\n• IDBI Green Home Loan Scheme' }
                      ]);
                    } else if (item.label === "Settings") {
                      setMessages(prev => [
                        ...prev,
                        { role: 'assistant', content: '⚙️ System Settings:\n• AI Model Engine: Gemini 2.0 Flash (Optimized)\n• Security Protocol: SSL/TLS 256-bit Encrypted' }
                      ]);
                    }
                  }}
                  className={`flex items-center gap-3 rounded-2xl px-3 py-2.5 text-[13.5px] font-medium transition-colors ${
                    isActive
                      ? "bg-white/[0.08] text-white glow-dark"
                      : "text-white/60 hover:bg-white/[0.04] hover:text-white"
                  }`}
                >
                  <item.icon className="h-[18px] w-[18px]" strokeWidth={2} />
                  <span>{item.label}</span>
                </motion.button>
              );
            })}
          </nav>

          <div className="mt-8 px-2">
             <div className="text-xs font-semibold text-white/50 mb-1 block">Connection Status</div>
             <div className="w-full bg-brand-green/20 border border-brand-green/50 rounded-xl px-3 py-2 text-sm text-brand-green outline-none flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-brand-green animate-pulse"></span>
                Securely Connected
             </div>
          </div>

          <div className="mt-auto rounded-3xl bg-white/[0.04] p-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-brand-pink text-ink font-bold">A</div>
              <div className="flex-1 min-w-0">
                <div className="truncate text-sm font-semibold text-white">Agent Alpha</div>
                <div className="truncate text-xs text-white/50">IDBI Staff</div>
              </div>
            </div>
          </div>
        </aside>

        {/* MAIN CHAT AREA */}
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden bg-white rounded-[28px] shadow-soft">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-black/5">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full overflow-hidden bg-[#FEF3D7] flex items-center justify-center">
                 <img src={mascot} alt="Mascot" className="h-10 w-10 object-contain" onError={(e) => e.currentTarget.style.display='none'} />
              </div>
              <div>
                <h2 className="text-lg font-bold">ProspectIQ Assistant - {activeNav}</h2>
                <div className="flex items-center gap-2 text-sm font-medium text-ink-soft">
                   <span className="flex h-2 w-2 rounded-full bg-brand-green"></span>
                   Online • Powered by Gemini
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
               <div className="text-xs font-bold uppercase tracking-wider text-ink-soft bg-canvas px-4 py-2 rounded-full">
                  Stage: <span className="text-[#F5A623]">{stage}</span>
               </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 scrollbar-none flex flex-col gap-6">
            <AnimatePresence>
              {messages.map((msg, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[75%] rounded-2xl p-4 ${
                    msg.role === 'user' 
                      ? 'bg-sidebar text-white rounded-tr-sm' 
                      : 'bg-canvas text-ink rounded-tl-sm'
                  }`}>
                    <p className="text-[15px] font-medium leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    
                    {/* Render Lead Card if present */}
                    {msg.lead && (
                       <div className="mt-4 bg-white border border-brand-yellow/30 rounded-xl p-4 shadow-sm text-ink">
                          <div className="flex items-center gap-2 text-brand-yellow font-bold mb-2">
                             <Sparkles className="h-4 w-4" /> Lead Captured
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                             <div className="text-ink-soft">Name: <span className="font-semibold text-ink">{msg.lead.name}</span></div>
                             <div className="text-ink-soft">Product: <span className="font-semibold text-ink">{msg.lead.product}</span></div>
                             <div className="text-ink-soft">Income: <span className="font-semibold text-ink">₹{msg.lead.income}</span></div>
                          </div>
                          <div className="mt-3 flex items-center justify-between border-t pt-3">
                             <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${
                               msg.lead.tag === 'HOT' ? 'bg-red-500' : msg.lead.tag === 'WARM' ? 'bg-orange-500' : 'bg-blue-500'
                             }`}>
                               {msg.lead.tag} PRIORITY
                             </span>
                             <span className="font-bold text-brand-green">Score: {msg.lead.score}/99</span>
                          </div>
                       </div>
                    )}
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                  <div className="bg-canvas rounded-2xl rounded-tl-sm p-4 flex gap-2 items-center">
                    <span className="w-2 h-2 bg-ink-soft rounded-full animate-bounce"></span>
                    <span className="w-2 h-2 bg-ink-soft rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                    <span className="w-2 h-2 bg-ink-soft rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-6 pt-0">
            <div className="flex items-end gap-3 bg-canvas p-2 rounded-[24px] border border-black/5">
              <button onClick={() => fileInputRef.current?.click()} className="grid h-[50px] w-[50px] shrink-0 place-items-center rounded-full text-ink-soft hover:bg-white hover:text-ink transition">
                <Paperclip className="h-[20px] w-[20px]" />
              </button>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about IDBI Bank products..."
                className="flex-1 bg-transparent max-h-[120px] min-h-[50px] resize-none py-3 px-2 text-[15px] font-medium text-ink placeholder:text-ink-soft/60 outline-none scrollbar-none z-10 pointer-events-auto"
                rows={1}
                disabled={isLoading}
              />
              <button onClick={() => handleQuickAction("Voice")} className="grid h-[50px] w-[50px] shrink-0 place-items-center rounded-full text-ink-soft hover:bg-white hover:text-ink transition">
                <Mic className="h-[20px] w-[20px]" />
              </button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isLoading}
                className="grid h-[50px] w-[50px] shrink-0 place-items-center rounded-full bg-sidebar text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ArrowUp className="h-[20px] w-[20px]" strokeWidth={2.5} />
              </motion.button>
            </div>
            <div className="text-center mt-3 text-[11px] font-medium text-ink-soft/60">
              AI can make mistakes. Consider verifying important information.
            </div>
          </div>
        </main>

        {/* RIGHT PANEL (Utility) */}
        <aside className="hidden xl:flex w-[27%] min-w-[320px] flex-col rounded-[36px] bg-sidebar p-6 text-sidebar-foreground">
          <div className="flex items-center justify-between">
            <h3 className="text-[15px] font-bold tracking-tight text-white">Quick Tools</h3>
          </div>

          <div className="mt-4 grid grid-cols-4 gap-2">
            {quickActions.map((a) => (
              <motion.button
                key={a.label}
                whileHover={{ y: -3, scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleQuickAction(a.label)}
                className="flex flex-col items-center gap-2"
              >
                <div className={`grid h-12 w-12 place-items-center rounded-full ${a.color} text-ink shadow-soft`}>
                  <a.icon className="h-[18px] w-[18px]" strokeWidth={2.3} />
                </div>
                <span className="text-[10.5px] font-semibold text-white/70 text-center leading-tight">{a.label}</span>
              </motion.button>
            ))}
          </div>

          {/* Lead Funnel Status */}
          <div className="mt-8">
            <h3 className="text-[15px] font-bold tracking-tight text-white mb-4">Funnel Activity</h3>
            <div className="bg-white/5 rounded-2xl p-4">
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${stage === 'identify' ? 'bg-[#F5A623] shadow-[0_0_10px_#F5A623]' : 'bg-white/20'}`}></div>
                  <span className={`text-sm font-semibold ${stage === 'identify' ? 'text-white' : 'text-white/50'}`}>1. Identify Needs</span>
                </div>
                <div className="w-[2px] h-4 bg-white/10 ml-1.5 -my-1"></div>
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${stage === 'engage' ? 'bg-brand-pink shadow-[0_0_10px_#F3A9D8]' : 'bg-white/20'}`}></div>
                  <span className={`text-sm font-semibold ${stage === 'engage' ? 'text-white' : 'text-white/50'}`}>2. Engage & Explain</span>
                </div>
                <div className="w-[2px] h-4 bg-white/10 ml-1.5 -my-1"></div>
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${stage === 'convert' ? 'bg-brand-green shadow-[0_0_10px_#57D48D]' : 'bg-white/20'}`}></div>
                  <span className={`text-sm font-semibold ${stage === 'convert' ? 'text-white' : 'text-white/50'}`}>3. Convert Lead</span>
                </div>
              </div>
            </div>
          </div>
          
        </aside>
      </div>
    </div>
  );
}
