import { useEffect, useRef, useState } from "react";
import "./App.css";
import carGif from "./assets/car.gif";

function App() {
  const [overtakedata, setOvertakeData] = useState({});
  const [cliffData, setCliffData] = useState({});
  const [undercutData, setUndercutData] = useState({});
  const [strategy, setStrategy] = useState("Not enough Data");

  const overtakeRefresh = useRef(0);
  const cliffRefresh = useRef(0);
  const undercutRefresh = useRef(0);

  // --- WebSocket logic extracted into a separate function ---
  const connectWebSocket = () => {
    const ws = new WebSocket("ws://localhost:8000/ws/overtakes");

    ws.onopen = () => console.log("✅ Connected to WebSocket!");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      console.log("📊 Latest overtake counts:", msg);

      // Filter out "refresh_count" and only keep drivers with value > 0
      const filtered = Object.fromEntries(
        Object.entries(msg).filter(
          ([key, value]) => key !== "refresh_count" && value > 0
        )
      );
      setOvertakeData(filtered);
      localStorage.setItem("overtake", JSON.stringify(filtered));
      overtakeRefresh.current = msg.refresh_count || 0;
      tryCallGemini();
    };

    ws.onclose = () => console.log("⚠️ WebSocket closed.");
    ws.onerror = (err) => console.error("❌ WebSocket error:", err);

    return ws;
  };

  const cliffProbability = () => {
    const ws = new WebSocket("ws://localhost:8001/ws/cliff");

    ws.onopen = () => console.log("✅ Connected to cliff!");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("📊 Latest tire cliff data:", data);

      // Remove refresh_count and keep drivers only
      const driversData = Object.fromEntries(
        Object.entries(data).filter(([key]) => key !== "refresh_count")
      );
      console.log("cliff", event.data.refresh_count);

      setCliffData(driversData?.MY_CAR);
      localStorage.setItem("cliff", JSON.stringify(driversData?.MY_CAR));
      cliffRefresh.current = event.data.refresh_countt || 0;
      tryCallGemini();
    };

    ws.onclose = () => console.log("⚠️ WebSocket closed.");
    ws.onerror = (err) => console.error("❌ WebSocket error:", err);

    return ws; // Optional: return ws for cleanup
  };

  const undercutProbability = () => {
    const ws = new WebSocket("ws://localhost:8002/ws/undercuts");

    ws.onopen = () => console.log("✅ Connected to undercit!");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("📊 Latest undercut  data:", data);

      // Remove refresh_count and keep drivers only
      const driversData = Object.fromEntries(
        Object.entries(data).filter(([key]) => key !== "refresh_count")
      );
      console.log("undercut", driversData);
      undercutRefresh.current = event.data.refresh_count || 0;

      setUndercutData(driversData?.MY_CAR);
      localStorage.setItem("undercuts", JSON.stringify(driversData?.MY_CAR));
      tryCallGemini();
    };

    ws.onclose = () => console.log("⚠️ WebSocket closed.");
    ws.onerror = (err) => console.error("❌ WebSocket error:", err);

    return ws; // Optional: return ws for cleanup
  };

  const callGeminiStrategy = async () => {
    try {
      const overtake = JSON.parse(localStorage.getItem("overtake") || "{}");
      const cliff = JSON.parse(localStorage.getItem("cliff") || "{}");
      const undercut = JSON.parse(localStorage.getItem("undercuts") || "{}");

      console.log("sending", overtake, cliff, undercut);

      const response = await fetch("http://localhost:8010/api/strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          overtake_data: overtake,
          tire_data: cliff,
          pit_data: undercut,
        }),
      });

      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      const data = await response.json();
      console.log("🧠 Gemini Strategy:", data.strategy);
      setStrategy(data.strategy);
    } catch (error) {
      console.error("❌ Gemini API call failed:", error);
    }
  };

  const tryCallGemini = () => {
    if (
      overtakeRefresh.current % 10 === 0 &&
      cliffRefresh.current % 10 === 0 &&
      undercutRefresh.current % 10 === 0
    ) {
      console.log("⏱️ Aggregated 5-refresh snapshot, calling Gemini...");
      callGeminiStrategy(overtakedata, cliffData, undercutData);
    } else {
      console.log(
        "na",
        overtakeRefresh.current,
        cliffRefresh.current,
        undercutRefresh.current
      );
    }
  };

  // --- Initialize WebSocket once ---
  useEffect(() => {
    const overtake = connectWebSocket();
    const cliff = cliffProbability();
    const undercut = undercutProbability();

    return () => {
      overtake.close();
      cliff.close();
      undercut.close();
    };
  }, []);

  return (
  <div className="bg-black w-full h-screen flex flex-row p-4 gap-4">
    {/* Left Metrics Panel */}
    <div className="w-7/12 h-full flex flex-col gap-4 overflow-y-auto pr-2">
      {/* Gemini Strategy */}
      <div className="bg-slate-800 p-4 rounded-2xl text-white shadow-lg">
        <h2 className="text-xl font-bold mb-2 text-yellow-400">🧠 Strategy</h2>
        <p className="text-gray-200">{strategy}</p>
      </div>

      {/* Overtake Probabilities */}
      <div className="bg-slate-900 p-4 rounded-2xl text-white shadow-lg">
        <h2 className="text-xl font-bold mb-4 text-pink-400">🏎️ F1 Overtaking Probability</h2>
        <div className="space-y-3">
          {Object.keys(overtakedata).length === 0 ? (
            <div className="text-gray-400">Waiting for data...</div>
          ) : (
            Object.entries(overtakedata).map(([driver, count]) => {
              const widthPercent = Math.min(count * 10, 100);
              return (
                <div key={driver}>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="font-medium">{driver}</span>
                    <span className="text-gray-400">{count}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-pink-400 h-2 rounded-full transition-all duration-700 ease-in-out"
                      style={{ width: `${widthPercent}%` }}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Tire Cliff */}
      <div className="bg-slate-800 p-4 rounded-2xl flex-1 text-white shadow-lg">
        <h2 className="text-xl font-semibold mb-3 text-red-400">⚠️ Tire Cliff Risk</h2>
        {cliffData ? (
          <>
            <p><span className="font-medium text-gray-300">Matches Found:</span> {cliffData.matches_found}</p>
            <p><span className="font-medium text-gray-300">Max Similarity:</span> {cliffData.max_similarity}</p>
            <p>
              <span className="font-medium text-gray-300">Risk Detected:</span>{" "}
              {cliffData.risk_detected ? (
                <span className="text-red-400 font-semibold">Yes ⚠️</span>
              ) : (
                <span className="text-green-400 font-semibold">No ✅</span>
              )}
            </p>
            <div className="mt-3">
              <span className="font-medium text-gray-300">Simulated Vector:</span>
              <div className="bg-gray-700 rounded-lg mt-1 p-2 text-sm text-gray-200">
                [{Array.isArray(cliffData?.simulated_vector) ? cliffData.simulated_vector.join(", ") : "N/A"}]
              </div>
            </div>
          </>
        ) : (
          <p className="text-gray-500">No cliff data available.</p>
        )}
      </div>

      {/* Undercut Analysis */}
      <div className="bg-slate-800 p-4 rounded-2xl flex-1 text-white shadow-lg">
        <h2 className="text-xl font-semibold mb-3 text-blue-400">🔵 Undercut Analysis</h2>
        {undercutData ? (
          <>
            <p><span className="font-medium text-gray-300">Total Matches:</span> {undercutData.total_matches}</p>
            <p><span className="font-medium text-gray-300">Relevant Matches:</span> {undercutData.relevant_matches}</p>
            <p className="mt-2 text-gray-300">
              {undercutData.relevant_matches < undercutData.total_matches
                ? `📊 Recommendation: Rival hasn’t pitted in ${undercutData.relevant_matches} out of ${undercutData.total_matches} similar scenarios.`
                : "✅ Safe: No similar scenarios where rival is yet to pit."}
            </p>
            <div className="mt-3">
              <span className="font-medium text-gray-300">Simulated Vector:</span>
              <div className="bg-gray-700 rounded-lg mt-1 p-2 text-sm text-gray-200">
                [{Array.isArray(undercutData?.simulated_vector) ? undercutData.simulated_vector.join(", ") : "N/A"}]
              </div>
            </div>
          </>
        ) : (
          <p className="text-gray-500">No undercut data available.</p>
        )}
      </div>
    </div>

    {/* Right Car GIF Panel */}
    <div className="w-5/12 h-full flex items-center justify-center overflow-hidden rounded-2xl">
      <img
        src={carGif}
        alt="Car"
        className="w-full h-full object-cover animate-pulse" // you can replace `animate-pulse` with a smooth CSS keyframe if needed
      />
    </div>
  </div>
);

}

export default App;
