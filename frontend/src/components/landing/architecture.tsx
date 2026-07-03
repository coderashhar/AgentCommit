"use client";

import { motion } from "framer-motion";
import { Bot, User, ArrowDown, ArrowRight } from "lucide-react";

const agents = [
  { name: "Profile Agent", emoji: "👤", delay: 0.1 },
  { name: "Repo Agent", emoji: "📦", delay: 0.2 },
  { name: "Issue Agent", emoji: "🔍", delay: 0.3 },
  { name: "Mentor Agent", emoji: "🎓", delay: 0.4 },
  { name: "PR Review", emoji: "✅", delay: 0.5 },
];

const workflow = [
  { step: "1", label: "Sign In", description: "Connect your GitHub account" },
  { step: "2", label: "Analyze", description: "AI analyzes your profile" },
  { step: "3", label: "Discover", description: "Find matching repos & issues" },
  { step: "4", label: "Learn", description: "Get AI explanations" },
  { step: "5", label: "Contribute", description: "Submit your PR with confidence" },
];

export function Architecture() {
  return (
    <section id="architecture" className="py-24 sm:py-32 bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Multi-Agent <span className="gradient-text">Architecture</span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
            Powered by Google ADK, specialized AI agents collaborate to provide
            a seamless mentoring experience.
          </p>
        </motion.div>

        {/* Agent visualization */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative max-w-4xl mx-auto mb-20"
        >
          {/* User node */}
          <div className="flex justify-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              transition={{ type: "spring", delay: 0 }}
              className="flex flex-col items-center"
            >
              <div className="w-16 h-16 rounded-2xl gradient-brand flex items-center justify-center shadow-lg shadow-primary/25">
                <User className="h-8 w-8 text-white" />
              </div>
              <span className="text-sm font-medium mt-2">You</span>
            </motion.div>
          </div>

          <div className="flex justify-center mb-8">
            <ArrowDown className="h-6 w-6 text-muted-foreground animate-bounce" />
          </div>

          {/* Coordinator */}
          <div className="flex justify-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              transition={{ type: "spring", delay: 0.05 }}
              className="flex flex-col items-center"
            >
              <div className="w-20 h-20 rounded-2xl bg-card border-2 border-primary/50 flex items-center justify-center shadow-lg">
                <Bot className="h-10 w-10 text-primary" />
              </div>
              <span className="text-sm font-semibold mt-2">Coordinator Agent</span>
              <span className="text-xs text-muted-foreground">Orchestrates all agents</span>
            </motion.div>
          </div>

          <div className="flex justify-center mb-8">
            <ArrowDown className="h-6 w-6 text-muted-foreground" />
          </div>

          {/* Sub-agents */}
          <div className="flex flex-wrap justify-center gap-4 sm:gap-6">
            {agents.map((agent) => (
              <motion.div
                key={agent.name}
                initial={{ scale: 0, opacity: 0 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ type: "spring", delay: agent.delay }}
                whileHover={{ scale: 1.05, y: -4 }}
                className="flex flex-col items-center"
              >
                <div className="w-14 h-14 rounded-xl bg-card border border-border/50 flex items-center justify-center shadow-md hover:shadow-lg hover:border-primary/30 transition-all duration-300">
                  <span className="text-2xl">{agent.emoji}</span>
                </div>
                <span className="text-xs font-medium mt-2 text-center">{agent.name}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Workflow steps */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto"
        >
          <h3 className="text-xl font-semibold text-center mb-10">
            How It Works
          </h3>
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            {workflow.map((item, index) => (
              <div key={item.step} className="flex items-center gap-3 sm:gap-0 sm:flex-col">
                <motion.div
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="flex flex-col items-center"
                >
                  <div className="w-10 h-10 rounded-full gradient-brand flex items-center justify-center text-white font-bold text-sm shadow-md">
                    {item.step}
                  </div>
                  <p className="text-sm font-semibold mt-2">{item.label}</p>
                  <p className="text-xs text-muted-foreground text-center mt-1 max-w-24">
                    {item.description}
                  </p>
                </motion.div>
                {index < workflow.length - 1 && (
                  <ArrowRight className="hidden sm:block h-4 w-4 text-muted-foreground mx-2 mt-[-24px]" />
                )}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
