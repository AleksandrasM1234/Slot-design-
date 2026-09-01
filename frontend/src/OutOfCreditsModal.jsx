export default function OutOfCreditsModal({ service, onClose }) {
  const isLeonardo = service === "leonardo";

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100]" onClick={onClose}>
      <div className="bg-white rounded-lg p-6 w-[420px]" onClick={(e) => e.stopPropagation()}>
        <div className="text-2xl mb-2">⚠️</div>
        <h3 className="text-lg font-bold mb-2">
          {isLeonardo ? "Leonardo credits ran out" : "Groq usage limit reached"}
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          {isLeonardo
            ? "Your Leonardo API balance is too low to complete this generation. Top up your credits to keep generating assets."
            : "The AI prompt enhancer has hit its usage limit for now. Wait a bit and try again, or check your Groq account for details."}
        </p>
        <div className="flex gap-2">
            <a
            href={isLeonardo ? "https://app.leonardo.ai/api-access" : "https://console.groq.com/settings/billing"}
            target="_blank"
            rel="noreferrer"
            className="border rounded p-2 bg-blue-500 text-white text-sm flex-1 text-center"
        >
            {isLeonardo ? "Top up Leonardo" : "Check Groq account"}
          </a>
          <button className="border rounded p-2 text-sm" onClick={onClose}>
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}