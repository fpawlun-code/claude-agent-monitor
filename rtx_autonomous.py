import os
from datetime import datetime, timedelta
import json
import time
from typing import Any

class RTXAutonomous:
    """
    Class for running autonomous missions.

    Args:
        objective (str): The objective of the mission.
        work_dir (str): Directory where progress and logs are stored.
    """

    def __init__(self, objective: str, work_dir: str):
        self.objective = objective
        self.work_dir = work_dir
        self.progress_file = os.path.join(work_dir, "progress.json")
        self.log_file = os.path.join(work_dir, "rtx_log.txt")

        # Load progress if available
        try:
            with open(self.progress_file, 'r') as f:
                self.progress = json.load(f)
        except FileNotFoundError:
            self.progress = {"start_time": str(datetime.now()), "status": "init"}

    def start_autonomous_mission(self) -> None:
        """
        Start the autonomous mission and save progress every 10 minutes.
        Stops when STOP file is found in work_dir or when interrupted.
        """
        while True:
            # Simulate some action
            action = f"Action {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            print(action)

            with open(self.log_file, 'a') as log:
                log.write(f"{action}\n")

            self.progress["status"] = "running"
            self.save_progress()

            if os.path.exists(os.path.join(self.work_dir, "STOP")):
                break

            time.sleep(600)  # Sleep for 10 minutes

    def save_progress(self) -> None:
        """
        Save the current progress to a JSON file.
        """
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f)

if __name__ == "__main__":
    work_dir = "autonomous_work"
    os.makedirs(work_dir, exist_ok=True)

    autonomous_mission = RTXAutonomous(objective="Explore the universe", work_dir=work_dir)
    autonomous_mission.start_autonomous_mission()
