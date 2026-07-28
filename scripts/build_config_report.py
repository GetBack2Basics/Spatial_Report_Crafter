#!/usr/bin/env python3
import os
import sys
import json
import argparse
import traceback
import pandas as pd
from dotenv import load_dotenv
from wherobots.db import connect
from shapely import wkt
from shapely.geometry import mapping

# Load environment
load_dotenv()
API_KEY = os.getenv("WHEROBOTS_API_KEY")
sys.stdout.reconfigure(encoding='utf-8')

def to_geojson_feature(wkt_str, properties=None):
    if not wkt_str:
        return None
    try:
        geom = wkt.loads(wkt_str)
        return {
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": properties or {}
        }
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description="Config-driven Wherobots Spatial HTML Report Generator")
    parser.add_argument("--config", required=True, help="Path to JSON configuration file")
    parser.add_argument("--template", required=True, help="Path to HTML template file")
    parser.add_argument("--output", default="runner/national_suitability_report.html", help="Path to output HTML file")
    args = parser.parse_args()

    # Load Config
    print(f"[1/8] Loading configuration from {args.config}...")
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Connect to Wherobots
    print("[2/8] Connecting to Wherobots Spatial SQL API...")
    try:
        conn = connect(api_key=API_KEY)
        cursor = conn.cursor()

        # Ingest local vector layers
        local_layers_data = {}
        total_layers = len(cfg.get("local_vector_layers", []))
        
        for idx, layer_cfg in enumerate(cfg.get("local_vector_layers", [])):
            layer_name = layer_cfg["name"]
            query = layer_cfg["query"]
            placeholder = layer_cfg["placeholder"]
            props_map = layer_cfg.get("properties_map", {})
            geom_idx = layer_cfg.get("geometry_index", 1)

            print(f"[{3 + idx}/8] Fetching local vector layer: {layer_name}...")
            cursor.execute(query)
            df_layer = cursor.fetchall()
            
            features = []
            for item_idx, row in df_layer.iterrows():
                properties = {}
                for p_key, p_idx in props_map.items():
                    val = row.iloc[p_idx]
                    properties[p_key] = int(val) if isinstance(val, (int, float, int)) and not pd.isna(val) else str(val)
                
                f = to_geojson_feature(row.iloc[geom_idx], properties)
                if f:
                    features.append(f)
                    
            geojson_col = {"type": "FeatureCollection", "features": features}
            local_layers_data[placeholder] = geojson_col

        # Run main suitability query
        main_query_idx = 3 + total_layers
        print(f"[{main_query_idx}/8] Executing main spatial suitability query on Wherobots...")
        main_query = cfg["wherobots_queries"]["main_suitability"]
        cursor.execute(main_query)
        df = cursor.fetchall()
        print(f"DEBUG: Retrieved {len(df)} candidate rows from Wherobots.")

        # Build list of dicts for candidates
        candidates = []
        for index, row in df.iterrows():
            candidates.append({
                "mb_code21": str(row["mb_code21"]),
                "mb_cat21": str(row["mb_cat21"]),
                "town_name": str(row["town_name"]),
                "region_name": str(row["region_name"]),
                "state_name": str(row["state_name"]),
                "surrounding_population_2020": float(row["surrounding_population_2020"]) if row["surrounding_population_2020"] is not None else 0.0,
                "surrounding_population_2030_predicted": float(row["surrounding_population_2030_predicted"]) if row["surrounding_population_2030_predicted"] is not None else 0.0,
                "dist_to_substation_km": float(row["dist_to_substation_km"]) if row["dist_to_substation_km"] is not None and not pd.isna(row["dist_to_substation_km"]) else None,
                "dist_to_wwtw_km": float(row["dist_to_wwtw_km"]) if row["dist_to_wwtw_km"] is not None and not pd.isna(row["dist_to_wwtw_km"]) else None,
                "area_ha": float(row["area_ha"]) if row["area_ha"] is not None else 0.0,
                "power_score": float(row["power_score"]) if row["power_score"] is not None else 0.0,
                "water_score": float(row["water_score"]) if row["water_score"] is not None else 0.0,
                "size_score": float(row["size_score"]) if row["size_score"] is not None else 0.0,
                "suitability_score": float(row["suitability_score"]) if row["suitability_score"] is not None else 0.0,
                "geometry": str(row["geometry"])
            })

        # Sort and limit candidates to top 5 NSW
        candidates.sort(key=lambda x: x["suitability_score"], reverse=True)
        candidates = candidates[:5]
        print(f"DEBUG: Selected top {len(candidates)} NSW candidates.")

        # Append simulated interstate benchmarks
        simulated = cfg.get("simulated_candidates", [])
        candidates.extend(simulated)
        candidates.sort(key=lambda x: x["suitability_score"], reverse=True)
        print(f"DEBUG: Total sorted benchmarking candidates count: {len(candidates)}")

        # Aggregate states and regions
        states = {}
        regions = {}
        for c in candidates:
            st = c["state_name"]
            if st not in states:
                states[st] = {"state_name": st, "candidate_count": 0, "sum_suit": 0.0, "sum_area": 0.0, "sum_pow": 0.0, "sum_wat": 0.0}
            states[st]["candidate_count"] += 1
            states[st]["sum_suit"] += c["suitability_score"]
            states[st]["sum_area"] += c["area_ha"]
            states[st]["sum_pow"] += c["dist_to_substation_km"] if c["dist_to_substation_km"] is not None else 0.0
            states[st]["sum_wat"] += c["dist_to_wwtw_km"] if c["dist_to_wwtw_km"] is not None else 0.0

            reg = (c["region_name"], c["state_name"])
            if reg not in regions:
                regions[reg] = {"region_name": c["region_name"], "state_name": st, "candidate_count": 0, "sum_suit": 0.0, "sum_area": 0.0, "sum_pow": 0.0, "sum_wat": 0.0}
            regions[reg]["candidate_count"] += 1
            regions[reg]["sum_suit"] += c["suitability_score"]
            regions[reg]["sum_area"] += c["area_ha"]
            regions[reg]["sum_pow"] += c["dist_to_substation_km"] if c["dist_to_substation_km"] is not None else 0.0
            regions[reg]["sum_wat"] += c["dist_to_wwtw_km"] if c["dist_to_wwtw_km"] is not None else 0.0

        state_list = []
        for s in states.values():
            n = s["candidate_count"]
            state_list.append({
                "state_name": s["state_name"],
                "candidate_count": n,
                "avg_suitability_score": s["sum_suit"] / n,
                "avg_area_ha": s["sum_area"] / n,
                "avg_dist_substation_km": s["sum_pow"] / n,
                "avg_dist_wwtw_km": s["sum_wat"] / n
            })
        state_list.sort(key=lambda x: x["avg_suitability_score"], reverse=True)

        region_list = []
        for r in regions.values():
            n = r["candidate_count"]
            region_list.append({
                "region_name": r["region_name"],
                "state_name": r["state_name"],
                "candidate_count": n,
                "avg_suitability_score": r["sum_suit"] / n,
                "avg_area_ha": r["sum_area"] / n,
                "avg_dist_substation_km": r["sum_pow"] / n,
                "avg_dist_wwtw_km": r["sum_wat"] / n
            })
        region_list.sort(key=lambda x: x["avg_suitability_score"], reverse=True)

        # Rending Template
        print("[8/8] Generating HTML content and writing interactive report...")
        with open(args.template, "r", encoding="utf-8") as f_temp:
            html_content = f_temp.read()

        # Injections
        html_content = html_content.replace("{{ REPORT_TITLE }}", cfg.get("report_title", "Spatial Siting Report"))
        html_content = html_content.replace("{{ REPORT_SUBTITLE }}", cfg.get("report_subtitle", ""))
        html_content = html_content.replace("{{ CANDIDATES_JSON }}", json.dumps(candidates))
        html_content = html_content.replace("{{ STATE_JSON }}", json.dumps(state_list))
        html_content = html_content.replace("{{ REGION_JSON }}", json.dumps(region_list))

        # Local vector overlays injection
        for placeholder, geojson_col in local_layers_data.items():
            html_content = html_content.replace(placeholder, json.dumps(geojson_col))

        # Output file
        abs_output = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(abs_output), exist_ok=True)
        with open(abs_output, "w", encoding="utf-8") as f_out:
            f_out.write(html_content)

        print(f"Report built successfully. Written size: {os.path.getsize(abs_output)}")
        print(f"File saved to: {abs_output}")

    except Exception as e:
        print("Error compiling report:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
