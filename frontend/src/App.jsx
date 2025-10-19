import { useEffect, useState } from "react";
import "./App.css";
import carGif from "./assets/car.gif";

function App() {
  const [overtakedata, setOvertakeData] = useState({});
  const [cliffData, setCliffData] = useState({});
  const [undercutData, setUndercutData] = useState({});

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
      console.log("cliff", driversData);

      setCliffData(driversData?.MY_CAR);
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

      setUndercutData(driversData?.MY_CAR);
    };

    ws.onclose = () => console.log("⚠️ WebSocket closed.");
    ws.onerror = (err) => console.error("❌ WebSocket error:", err);

    return ws; // Optional: return ws for cleanup
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
    <div className="bg-black w-full h-screen flex flex-row p-2 gap-1">
      <div className="w-[70%] h-full flex flex-col gap-1">
        <div className="w-full h-24  bg-slate-800 p-2 text-white">
          llm goes here
        </div>
        <div className="w-full min-h-80 rounded-2xl text-white p-2">
          <h3 className="text-3xl font-bold mb-8">F1 Overtaking Probability</h3>
          <div className="space-y-4">
            {Object.keys(overtakedata).length === 0 ? (
              <div className="text-gray-400">Waiting for data...</div>
            ) : (
              Object.entries(overtakedata).map(([driver, count]) => {
                // Width = count * 10% (max 100%)
                const widthPercent = Math.min(count * 10, 100);

                return (
                  <div key={driver}>
                    <div className="flex justify-between mb-1 text-sm">
                      <span className="font-medium">{driver}</span>
                      <span className="text-gray-400">{count}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-white h-2 rounded-full transition-all duration-700 ease-in-out"
                        style={{ width: `${widthPercent}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
        <div className="w-full rounded-2xl flex-1 text-white p-2 ">
          <h2 className="text-xl font-semibold mb-3 text-red-400">
            Tire Cliff Risk
          </h2>
          {cliffData ? (
            <>
              <p>
                <span className="font-medium text-gray-300">
                  Matches Found:
                </span>{" "}
                {cliffData.matches_found}
              </p>
              <p>
                <span className="font-medium text-gray-300">
                  Max Similarity:
                </span>{" "}
                {cliffData.max_similarity}
              </p>
              <p>
                <span className="font-medium text-gray-300">
                  Risk Detected:
                </span>{" "}
                {cliffData.risk_detected ? (
                  <span className="text-red-400 font-semibold">Yes ⚠️</span>
                ) : (
                  <span className="text-green-400 font-semibold">No ✅</span>
                )}
              </p>

              <div className="mt-3">
                <span className="font-medium text-gray-300">
                  Simulated Vector:
                </span>
                <div className="bg-gray-700 rounded-lg mt-1 p-2 text-sm text-gray-200">
                [
                  {Array.isArray(cliffData?.simulated_vector)
                    ? cliffData.simulated_vector?.join(", ")
                    : cliffData?.simulated_vector || "N/A"}
                  ]
                </div>
              </div>
            </>
          ) : (
            <p className="text-gray-500">No cliff data available.</p>
          )}
        </div>
        <div className="w-full rounded-2xl flex-1 text-white p-2">
          <h2 className="text-xl font-semibold mb-3 text-blue-400">
            🧠 Undercut Analysis
          </h2>
          {undercutData ? (
            <>
              <p>
                <span className="font-medium text-gray-300">
                  Total Matches:
                </span>{" "}
                {undercutData.total_matches}
              </p>
              <p>
                <span className="font-medium text-gray-300">
                  Relevant Matches:
                </span>{" "}
                {undercutData.relevant_matches}
              </p>

              <p className="mt-2 text-gray-300">
                {undercutData.relevant_matches < undercutData.total_matches
                  ? `📊 Recommendation: Rival hasn’t pitted in ${undercutData.relevant_matches} out of ${undercutData.total_matches} similar scenarios.`
                  : "✅ Safe: No similar scenarios where rival is yet to pit."}
              </p>

              <div className="mt-3">
                <span className="font-medium text-gray-300">
                  Simulated Vector:
                </span>
                <div className="bg-gray-700 rounded-lg mt-1 p-2 text-sm text-gray-200">
                  [
                  {Array.isArray(undercutData?.simulated_vector)
                    ? cliffData.simulated_vector?.join(", ")
                    : cliffData?.simulated_vector || "N/A"}
                  ]
                </div>
              </div>
            </>
          ) : (
            <p className="text-gray-500">No undercut data available.</p>
          )}
        </div>
      </div>
      <div className=" w-[30%] h-full">
        <img
          src={carGif}
          alt="Car"
          className="w-full h-full object-cover rounded-2xl" // object-contain if you want to maintain aspect ratio
        />
      </div>
    </div>
  );
}

export default App;
