import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Camera, Server, Brain, Eye, Car, LayoutDashboard, Play } from 'lucide-react';

const NODES = {
  input: { x: '10%', y: '50%', label: 'Video Stream / IP Camera', icon: Camera, color: 'text-blue-400', border: 'border-blue-500/50', bg: 'bg-blue-500/10', glow: 'shadow-[0_0_20px_rgba(59,130,246,0.5)]' },
  core: { x: '35%', y: '50%', label: 'Master Thread: YOLOv8 + ByteTrack (Real-time Tracking)', icon: Server, color: 'text-neon-blue', border: 'border-neon-blue/50', bg: 'bg-neon-blue/10', glow: 'shadow-[0_0_30px_rgba(0,243,255,0.6)]' },
  worker1: { x: '65%', y: '20%', label: 'BLIP Transformer (Type & Color)', icon: Car, color: 'text-neon-purple', border: 'border-neon-purple/50', bg: 'bg-neon-purple/10', glow: 'shadow-[0_0_20px_rgba(176,38,255,0.5)]' },
  worker2: { x: '65%', y: '50%', label: 'EasyOCR Pipeline (ALPR)', icon: Brain, color: 'text-neon-purple', border: 'border-neon-purple/50', bg: 'bg-neon-purple/10', glow: 'shadow-[0_0_20px_rgba(176,38,255,0.5)]' },
  worker3: { x: '65%', y: '80%', label: 'CLIP Zero-Shot (Driver Behavior)', icon: Eye, color: 'text-neon-purple', border: 'border-neon-purple/50', bg: 'bg-neon-purple/10', glow: 'shadow-[0_0_20px_rgba(176,38,255,0.5)]' },
  output: { x: '90%', y: '50%', label: 'PyQt6 Live Dashboard', icon: LayoutDashboard, color: 'text-neon-green', border: 'border-neon-green/50', bg: 'bg-neon-green/10', glow: 'shadow-[0_0_30px_rgba(57,255,20,0.6)]' },
};

function DataPacket({ path, color, delay, isPlaying }: { path: any; color: string; delay: number; isPlaying: boolean }) {
  if (!isPlaying) return null;
  return (
    <motion.div
      initial={{ left: path.x[0], top: path.y[0], opacity: 0, scale: 0.5 }}
      animate={{ 
        left: path.x, 
        top: path.y, 
        opacity: [0, 1, 1, 0],
        scale: [0.5, 1.2, 1.2, 0.5] 
      }}
      transition={{ 
        duration: 3, 
        times: [0, 0.2, 0.8, 1], // Flow pacing
        ease: 'easeInOut',
        delay: delay,
        repeat: Infinity,
        repeatDelay: 0.5
      }}
      className={`absolute w-3 h-3 rounded-full -translate-x-1/2 -translate-y-1/2 z-50 shadow-[0_0_15px_currentColor] ${color}`}
    />
  );
}

function CurvedLine({ p1, p2, color = "stroke-dark-border" }: { p1: any; p2: any; color?: string }) {
  // Parsing percentage strings to numbers for SVG viewBox
  const x1 = parseFloat(p1.x) * 10;
  const y1 = parseFloat(p1.y) * 10;
  const x2 = parseFloat(p2.x) * 10;
  const y2 = parseFloat(p2.y) * 10;
  
  // Create a smooth cubic bezier curve
  const cx1 = x1 + (x2 - x1) / 2;
  const cy1 = y1;
  const cx2 = x1 + (x2 - x1) / 2;
  const cy2 = y2;

  return (
    <path 
      d={`M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`} 
      fill="none" 
      strokeWidth="2" 
      className={`${color} origin-center transition-colors duration-500`}
      strokeDasharray="8 8"
    />
  );
}

export default function App() {
  const [isPlaying, setIsPlaying] = useState(false);

  // Define the packet routes
  const routes = [
    { x: [NODES.input.x, NODES.core.x, NODES.worker1.x, NODES.output.x], y: [NODES.input.y, NODES.core.y, NODES.worker1.y, NODES.output.y], color: 'bg-neon-purple text-neon-purple' },
    { x: [NODES.input.x, NODES.core.x, NODES.worker2.x, NODES.output.x], y: [NODES.input.y, NODES.core.y, NODES.worker2.y, NODES.output.y], color: 'bg-neon-blue text-neon-blue' },
    { x: [NODES.input.x, NODES.core.x, NODES.worker3.x, NODES.output.x], y: [NODES.input.y, NODES.core.y, NODES.worker3.y, NODES.output.y], color: 'bg-neon-green text-neon-green' },
  ];

  return (
    <div className="min-h-screen bg-dark-bg text-white font-sans overflow-hidden py-10 px-4 flex flex-col items-center">
      
      {/* Header */}
      <div className="text-center mb-12 z-10 hidden md:block">
        <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-neon-blue via-neon-purple to-neon-green pb-2">
          Nexus: Traffic Intelligence Core
        </h1>
        <p className="text-gray-400 text-lg mt-2">Systems Architecture & Asynchronous Workflow Simulation</p>
      </div>

      {/* Main Diagram Area */}
      <div className="relative w-full max-w-6xl aspect-[16/9] border border-dark-border rounded-xl bg-dark-surface/50 backdrop-blur-sm overflow-hidden flex-shrink-0 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
        
        {/* Background Grid */}
        <div className="absolute inset-0 z-0 opacity-20" style={{ backgroundImage: 'linear-gradient(#2a2a35 1px, transparent 1px), linear-gradient(90deg, #2a2a35 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>

        {/* Static SVG Connections */}
        <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" className="absolute inset-0 w-full h-full z-0 opacity-60">
          <CurvedLine p1={NODES.input} p2={NODES.core} color={isPlaying ? "stroke-neon-blue opacity-50" : "stroke-dark-border"} />
          <CurvedLine p1={NODES.core} p2={NODES.worker1} color={isPlaying ? "stroke-neon-purple opacity-50" : "stroke-dark-border"} />
          <CurvedLine p1={NODES.core} p2={NODES.worker2} color={isPlaying ? "stroke-neon-purple opacity-50" : "stroke-dark-border"} />
          <CurvedLine p1={NODES.core} p2={NODES.worker3} color={isPlaying ? "stroke-neon-purple opacity-50" : "stroke-dark-border"} />
          <CurvedLine p1={NODES.worker1} p2={NODES.output} color={isPlaying ? "stroke-neon-green opacity-50" : "stroke-dark-border"} />
          <CurvedLine p1={NODES.worker2} p2={NODES.output} color={isPlaying ? "stroke-neon-green opacity-50" : "stroke-dark-border"} />
          <CurvedLine p1={NODES.worker3} p2={NODES.output} color={isPlaying ? "stroke-neon-green opacity-50" : "stroke-dark-border"} />
        </svg>

        {/* Data Packets */}
        {/* We generate multiple packets with different delays to simulate continuous stream */}
        {[0, 0.5, 1, 1.5, 2].map((delayFactor) => (
          <React.Fragment key={`packet-group-${delayFactor}`}>
             <DataPacket path={routes[0]} color={routes[0].color} delay={delayFactor} isPlaying={isPlaying} />
             <DataPacket path={routes[1]} color={routes[1].color} delay={delayFactor + 0.15} isPlaying={isPlaying} />
             <DataPacket path={routes[2]} color={routes[2].color} delay={delayFactor + 0.3} isPlaying={isPlaying} />
          </React.Fragment>
        ))}

        {/* Nodes rendering */}
        {Object.entries(NODES).map(([key, node]) => (
          <div 
            key={key}
            className={`absolute flex flex-col items-center justify-center transform -translate-x-1/2 -translate-y-1/2 z-10 w-48 transition-all duration-700 ${isPlaying ? 'scale-105' : 'scale-100'}`}
            style={{ left: node.x, top: node.y }}
          >
            <div className={`p-4 rounded-xl border ${node.border} ${node.bg} backdrop-blur-md flex flex-col items-center text-center gap-3 ${isPlaying ? node.glow : 'shadow-lg bg-[#0a0a0f]'} transition-all duration-500 relative`}>
              <node.icon className={`w-8 h-8 ${node.color} animate-pulse`} strokeWidth={1.5} />
              <span className={`text-xs font-semibold ${node.color} leading-snug tracking-wider uppercase`}>{node.label}</span>
              
              {/* Node connecting anchor points (purely decorative) */}
              <div className="absolute top-1/2 -left-1 w-2 h-2 rounded-full bg-dark-border -translate-y-1/2"></div>
              <div className="absolute top-1/2 -right-1 w-2 h-2 rounded-full bg-dark-border -translate-y-1/2"></div>
            </div>
          </div>
        ))}
      </div>

      {/* Control Button */}
      <button 
        onClick={() => setIsPlaying(!isPlaying)}
        className={`mt-10 px-8 py-4 rounded-full font-bold text-lg flex items-center gap-3 transition-all duration-300 shadow-xl z-20 ${
          isPlaying 
            ? 'bg-red-500/10 text-red-400 border border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.3)] hover:bg-red-500/20' 
            : 'bg-neon-blue/10 text-neon-blue border border-neon-blue/50 shadow-[0_0_30px_rgba(0,243,255,0.3)] hover:bg-neon-blue/20'
        }`}
      >
        <Play className={`w-5 h-5 ${isPlaying ? 'hidden' : 'block'}`} />
        <span className={`w-3 h-3 rounded-sm bg-red-400 ${isPlaying ? 'block' : 'hidden'}`}></span>
        {isPlaying ? 'Halt Simulation' : 'Run Pipeline Simulation'}
      </button>

    </div>
  );
}
