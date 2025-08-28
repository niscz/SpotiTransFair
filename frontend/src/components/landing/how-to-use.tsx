// frontend/src/components/landing/how-to-use.tsx
import { Card, CardContent } from "@/components/ui/card";

export default function HowToUse() {
    const steps = [
        {
            title: "Step 1",
            description: (
                <>
                    Log into YouTube Music at{" "}
                    <a
                        href="https://music.youtube.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                    >
                        music.youtube.com
                    </a>
                </>
            ),
        },
        {
            title: "Step 2",
            description:
                "Grab the Request Headers from the Network tab (explained later)",
        },
        {
            title: "Step 3",
            description: "Paste the playlist link and you're done!",
        },
    ];

    return (
        <div className="flex justify-center items-center">
            <div className="flex flex-col md:flex-row justify-center items-center gap-4 mb-10 w-full max-w-[1000px]">
                {steps.map((step, index) => (
                    <Card key={index} className="w-full max-w-sm h-48">
                        <CardContent className="flex flex-col mt-10 p-6 text-center h-full">
                            <h2 className="text-2xl font-bold">{step.title}</h2>
                            <p className="mt-2 text-sm text-gray-600">
                                {step.description}
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
