"""Stage: download San Francisco source data (footprints, parcels, assessor roll,
street trees, TIGER land/water).

Outputs (all under data/raw, never modified afterwards):
  sf_footprints/page-*.geojson   DataSF ynuv-fyni  Building Footprints (2016, LiDAR heights)
  sf_parcels/page-*.geojson      DataSF acdm-wktn  Parcels – Active and Retired
  sf_assessor_2025/page-*.json   DataSF wv5m-vpq2  Assessor Historical Secured Property Tax Rolls
  sf_street_trees/page-*.json    DataSF tkzw-k3nq  Street Tree List
  tiger/...                      Census TIGER/Line 2024 counties + area water
"""
from __future__ import annotations

from common import RAW, download_file, log, socrata_pages

ROLL_YEAR = "2025"  # latest closed_roll_year available (checked 2026-11)

BAY_COUNTIES = {
    "06001": "Alameda", "06013": "Contra Costa", "06041": "Marin", "06055": "Napa",
    "06075": "San Francisco", "06081": "San Mateo", "06085": "Santa Clara",
    "06095": "Solano", "06097": "Sonoma",
}


def main():
    socrata_pages(
        "ynuv-fyni", RAW / "sf_footprints", fmt="geojson",
        select="sf16_bldgid,mblr,hgt_median_m,hgt_maxcm,peak_1st_m,gnd_min_m,shape",
        page_size=50000,
    )
    socrata_pages(
        "acdm-wktn", RAW / "sf_parcels", fmt="geojson",
        select="mapblklot,blklot,block_num,lot_num,active,date_rec_add,date_rec_drop,"
               "date_map_add,date_map_drop,shape",
        page_size=50000,
    )
    socrata_pages(
        "wv5m-vpq2", RAW / f"sf_assessor_{ROLL_YEAR}",
        select="parcel_number,block,lot,property_location,year_property_built,"
               "number_of_stories,number_of_units,use_code,use_definition,"
               "property_class_code,property_class_code_definition,construction_type,"
               "property_area,lot_area",
        where=f"closed_roll_year='{ROLL_YEAR}'",
        page_size=50000,
    )
    socrata_pages(
        "tkzw-k3nq", RAW / "sf_street_trees",
        select="treeid,species,planteddate,mapdbh,latitude,longitude,legalstatus,planttype",
        page_size=50000,
    )
    socrata_pages(
        "3psu-pn9h", RAW / "sf_streets", fmt="geojson",
        select="cnn,street,st_type,streetname,f_node_cnn,t_node_cnn,active,layer,date_added,date_dropped,line",
        page_size=50000,
    )
    socrata_pages("3nje-yn2u", RAW / "sf_rpd_parks", fmt="geojson", page_size=50000)
    # DBI building permits: new construction (types 1, 2) and demolitions (6) that completed
    socrata_pages(
        "i98e-djp9", RAW / "sf_permits_newdemo",
        select="permit_number,permit_type,block,lot,status,filed_date,issued_date,completed_date,"
               "description,number_of_proposed_stories,proposed_units,existing_use,proposed_use,location",
        where="permit_type in ('1','2','6') AND completed_date IS NOT NULL",
        page_size=50000,
    )
    # Census TIGER/Line: county outlines (they extend into the water) + area water
    # polygons, used to derive a detailed modern land polygon.
    download_file("https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip",
                  RAW / "tiger" / "tl_2024_us_county.zip")
    for fips in BAY_COUNTIES:
        download_file(f"https://www2.census.gov/geo/tiger/TIGER2024/AREAWATER/tl_2024_{fips}_areawater.zip",
                      RAW / "tiger" / f"tl_2024_{fips}_areawater.zip")
    log("download_sf: done")


if __name__ == "__main__":
    main()
