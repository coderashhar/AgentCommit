"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
  User,
  GitFork,
  Search,
  BookOpen,
  GitPullRequest,
  MessageSquare,
} from "lucide-react";
import { motion } from "framer-motion";

const features = [
  {
    icon: User,
    title: "Profile Analysis",
    description:
      "AI analyzes your GitHub profile to understand your skills, languages, and experience level.",
    color: "text-blue-500",
    bg: "bg-blue-500/10",
  },
  {
    icon: GitFork,
    title: "Smart Repo Matching",
    description:
      "Get personalized repository recommendations based on your tech stack and interests.",
    color: "text-emerald-500",
    bg: "bg-emerald-500/10",
  },
  {
    icon: Search,
    title: "Issue Discovery",
    description:
      "Find beginner-friendly issues that match your skills across thousands of repositories.",
    color: "text-amber-500",
    bg: "bg-amber-500/10",
  },
  {
    icon: BookOpen,
    title: "AI Explanations",
    description:
      "Complex issues explained in plain English with difficulty ratings and learning resources.",
    color: "text-violet-500",
    bg: "bg-violet-500/10",
  },
  {
    icon: GitPullRequest,
    title: "PR Review",
    description:
      "Get AI-powered code reviews with actionable suggestions before submitting your PR.",
    color: "text-rose-500",
    bg: "bg-rose-500/10",
  },
  {
    icon: MessageSquare,
    title: "Commit Messages",
    description:
      "Generate professional conventional commit messages that follow best practices.",
    color: "text-cyan-500",
    bg: "bg-cyan-500/10",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function Features() {
  return (
    <section id="features" className="py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Everything You Need to{" "}
            <span className="gradient-text">Contribute</span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
            10 specialized AI agents work together to guide you from your
            very first open source contribution to becoming a confident contributor.
          </p>
        </motion.div>

        {/* Feature grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((feature) => (
            <motion.div key={feature.title} variants={itemVariants}>
              <Card className="group relative overflow-hidden border-border/50 hover:border-primary/30 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 h-full">
                <CardContent className="p-6">
                  <div
                    className={`inline-flex items-center justify-center rounded-xl p-3 ${feature.bg} mb-4 group-hover:scale-110 transition-transform duration-300`}
                  >
                    <feature.icon className={`h-6 w-6 ${feature.color}`} />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
