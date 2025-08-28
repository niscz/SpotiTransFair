// frontend/src/components/landing/footer.tsx

export function Footer() {
    return (
        <footer className="border-t w-full mt-28 py-12 text-center text-sm text-gray-500">
            <div className="container mx-auto px-4">
                <p className="mb-2">
                    Built by{" "}
                    <a
                        href="https://github.com/niscz"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline"
                    >
                        @niscz
                    </a>
                </p>
            </div>
        </footer>
    );
}
