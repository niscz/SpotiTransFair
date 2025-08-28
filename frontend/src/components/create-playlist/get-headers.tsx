// frontend/src/components/create-playlist/get-headers.tsx
import { Card, CardContent } from "@/components/ui/card";
import HeaderImg from "@/assets/headers.png";
import Navbar from "@/nav-bar";

type StepProps = {
    title: string;
    description: string | JSX.Element;
};

export default function GetHeaders() {
    const steps: StepProps[] = [
        {
            title: "Open Developer Tools and go to the Network tab",
            description:
                "Open the developer tools in your browser and go to the network tab. You can do this by right-clicking anywhere on the page and selecting 'Inspect' or by pressing 'Ctrl + Shift + I'.",
        },
        {
            title: "Sign into YouTube Music",
            description: (
                <>
                    Go to{" "}
                    <a
                        href="https://music.youtube.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                    >
                        music.youtube.com
                    </a>{" "}
                    and make sure you are signed in with your Google account.
                </>
            ),
        },
        {
            title: "Find an authenticated POST request",
            description: (
                <>
                    <p>
                        Filter by <code>{"/browse"}</code> in the search bar of
                        the Network tab. Find a POST request with a status of
                        200
                    </p>
                    <p className="mt-2">{"Firefox (recommended):"}</p>
                    <ul className="list-disc list-inside mb-2 ml-4">
                        <li>
                            Verify that the request looks like this:{" "}
                            <span className="font-bold">Status :</span> 200,{" "}
                            <span className="font-bold">Method :</span> POST,{" "}
                            <span className="font-bold">Domain :</span>{" "}
                            music.youtube.com,{" "}
                            <span className="font-bold">File :</span> browse?...{" "}
                        </li>
                        <li>
                            {
                                "Copy the request headers (right click > copy > copy request headers)"
                            }
                        </li>
                    </ul>

                    <p className="mb-2">{"Chromium based (Chrome/Edge):"}</p>
                    <ul className="list-disc list-inside mb-2 ml-4">
                        <li>
                            Verify that the request looks like this:{" "}
                            <span className="font-bold">Status :</span> 200,{" "}
                            <span className="font-bold">Name :</span> browse?...
                        </li>
                        <li>
                            {
                                "Click on the Name of any matching request. In the “Headers” tab, scroll to the section “Request headers” and copy everything starting from “accept: */*” to the end of the section"
                            }
                        </li>
                    </ul>
                </>
            ),
        },
        {
            title: "Paste the headers below",
            description:
                "We will be using these headers to authenticate the requests to create the playlist on your account.",
        },
    ];

    return (
        <>
            <div className="flex justify-center items-center w-[1000px]">
                <Navbar />
            </div>
            <div className="flex justify-center items-center my-10">
                <Card className="overflow-hidden w-[1000px]">
                    <div className="flex flex-col lg:flex-row">
                        <CardContent className="flex-1 p-6 lg:p-8">
                            <div className="space-y-6">
                                <div>
                                    <h2 className="mt-2 text-2xl lg:text-3xl font-semibold tracking-tight">
                                        How to get auth headers
                                    </h2>
                                </div>
                                <div className="space-y-5 mb-10">
                                    {steps.map((step, index) => (
                                        <Step
                                            key={index}
                                            index={index}
                                            title={step.title}
                                            description={step.description}
                                        />
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                        <div className="flex-1 bg-zinc-100 min-h-[300px] lg:min-h-0 hidden lg:block">
                            <img
                                src={HeaderImg}
                                alt="Password manager interface"
                                className="h-full w-full object-cover object-left-top"
                            />
                        </div>
                    </div>
                </Card>
            </div>
        </>
    );
}

function Step({ title, description, index }: StepProps & { index: number }) {
    return (
        <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-zinc-100 dark:bg-zinc-800 text-sm">
                    {index + 1}
                </span>
            </div>
            <div>
                <h3 className="font-medium">{title}</h3>
                <div className="text-sm text-zinc-500">{description}</div>
            </div>
        </div>
    );
}
