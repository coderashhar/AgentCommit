"use client";

import { Button } from "@/components/ui/button";
import { GitHubIcon } from "@/components/shared/github-icon";
import { Rocket } from "lucide-react";
import { motion } from "framer-motion";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

export function CTA() {
  const { status } = useSession();
  const router = useRouter();

  const handleGetStarted = () => {
    if (status === "authenticated") {
      router.push("/dashboard");
    } else {
      signIn("github", { callbackUrl: "/dashboard" });
    }
  };

  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="relative rounded-3xl overflow-hidden"
        >
          {/* Gradient background */}
          <div className="absolute inset-0 gradient-brand opacity-90" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(255,255,255,0.15),_transparent_50%)]" />

          <div className="relative px-8 py-16 sm:px-16 sm:py-20">
            <Rocket className="h-12 w-12 text-white/80 mx-auto mb-6" />
            <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
              Ready to Start Contributing?
            </h2>
            <p className="mt-4 text-lg text-white/80 max-w-xl mx-auto">
              Join AgentCommit and let AI guide you from your first issue
              to your first merged pull request.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                className="bg-white text-primary hover:bg-white/90 px-8 py-6 text-base font-semibold shadow-lg"
                onClick={handleGetStarted}
              >
                <GitHubIcon className="mr-2 h-5 w-5" />
                {status === "authenticated" ? "Go to Dashboard" : "Sign in with GitHub"}
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-white/30 text-white hover:bg-white/10 px-8 py-6 text-base"
                onClick={() => window.open("https://github.com/coderashhar/AgentCommit", "_blank")}
              >
                View on GitHub
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
