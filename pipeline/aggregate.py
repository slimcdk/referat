#!/usr/bin/env python3
"""Aggregates multiple processed meeting clips into a single joint meeting summary."""
import os
import sys
import json
import argparse

# Allow importing local files in pipeline directory
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from summarize import summarize

def aggregate_clips(meeting_id, title, clip_dirs, model="gemma3:4b", log=print):
    log(f"[aggregate] Aggregating {len(clip_dirs)} clips for meeting {meeting_id}...")

    # Create the consolidated output directory
    outdir = os.path.join(HERE, "output", f"meeting_{meeting_id}")
    os.makedirs(outdir, exist_ok=True)

    combined_segments = []
    combined_visuals = []
    
    cumulative_duration = 0.0

    for idx, clip_dir in enumerate(clip_dirs):
        clip_path = os.path.join(HERE, "output", clip_dir)
        if not os.path.exists(clip_path):
            log(f"[aggregate] WARNING: clip directory not found at {clip_path}")
            continue

        # 1. Process Segments
        seg_path = os.path.join(clip_path, "segments.json")
        if os.path.exists(seg_path):
            try:
                seg_data = json.load(open(seg_path))
                segments = seg_data.get("segments", [])
                
                # Offset timestamps for this clip
                for seg in segments:
                    offset_seg = seg.copy()
                    offset_seg["start"] = seg["start"] + cumulative_duration
                    offset_seg["end"] = seg["end"] + cumulative_duration
                    combined_segments.append(offset_seg)
                
                # Update cumulative duration
                duration = seg_data.get("duration", 0.0)
                if duration == 0.0 and segments:
                    duration = max(s["end"] for s in segments)
                cumulative_duration += duration
                
            except Exception as e:
                log(f"[aggregate] Error loading segments for clip {clip_dir}: {str(e)}")

        # 2. Process Keyframes/Visuals
        vis_path = os.path.join(clip_path, "visuals.json")
        if os.path.exists(vis_path):
            try:
                visuals = json.load(open(vis_path))
                # Offset timestamps for keyframes
                for vis in visuals:
                    offset_vis = vis.copy()
                    offset_vis["timestamp"] = vis["timestamp"] + cumulative_duration
                    # Copy keyframe images if needed (could be linked)
                    combined_visuals.append(offset_vis)
            except Exception as e:
                log(f"[aggregate] Error loading visuals for clip {clip_dir}: {str(e)}")

    # 3. Write combined segments.json
    seg_output = {
        "duration": cumulative_duration,
        "language": "da",
        "segments": combined_segments
    }
    with open(os.path.join(outdir, "segments.json"), "w", encoding="utf-8") as f:
        json.dump(seg_output, f, ensure_ascii=False, indent=2)

    # 4. Write combined visuals.json
    with open(os.path.join(outdir, "visuals.json"), "w", encoding="utf-8") as f:
        json.dump(combined_visuals, f, ensure_ascii=False, indent=2)

    log(f"[aggregate] Combined segments size: {len(combined_segments)}, visuals size: {len(combined_visuals)}")
    log(f"[aggregate] Cumulative duration: {cumulative_duration:.2f}s")

    # 5. Invoke standard summarize function on the aggregated data
    log(f"[aggregate] Triggering standard summary generator for combined meeting...")
    summarize(outdir, title, model=model, log=log)
    log(f"[aggregate] Aggregation complete for meeting {meeting_id}.")
    return outdir

def main():
    ap = argparse.ArgumentParser(description="Aggregate multiple processed clips into a single meeting.")
    ap.add_argument("meeting_id")
    ap.add_argument("title")
    ap.add_argument("clips", nargs="+", help="Folders of the clips (relative to pipeline/output/)")
    ap.add_argument("-m", "--model", default="gemma3:4b")
    a = ap.parse_args()
    
    aggregate_clips(a.meeting_id, a.title, a.clips, a.model)

if __name__ == "__main__":
    main()
