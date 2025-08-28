// frontend/src/pages/App.tsx
import Hero from "@/components/landing/hero.tsx";
import HowToUse from "@/components/landing/how-to-use.tsx";
import { Footer } from "@/components/landing/footer.tsx";

export default function App() {
    return (
        <main className="flex w-screen flex-col items-center justify-center">
            <div className="mb-10">
                <Hero />
            </div>
            <h2 className="mt-20 text-center mb-3 text-2xl font-bold mx-auto relative z-20 py-4 bg-clip-text text-transparent bg-gradient-to-b from-neutral-800 via-neutral-700 to-neutral-700 dark:from-neutral-800 dark:via-white dark:to-white w-full">
                How to use
            </h2>
            <HowToUse />
            <Footer />
        </main>
    );
}
