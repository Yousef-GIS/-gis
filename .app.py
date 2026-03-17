import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
from zipfile import ZipFile
import os
import tempfile

# إعدادات الصفحة
st.set_page_config(page_title="GIS Join Tool", layout="wide")

st.title("🌍 أداة الربط المكاني والوصفي (GIS Join Tool)")
st.markdown("---")

# --- شريط الجانبي (Sidebar) ---
st.sidebar.header("📁 رفع البيانات")

def load_data(uploaded_file):
    if uploaded_file is not None:
        suffix = os.path.splitext(uploaded_file.name)[1].lower()
        with tempfile.TemporaryDirectory() as tmpdir:
            if suffix == '.zip':
                # معالجة ملف Shapefile المضغوط
                zip_path = os.path.join(tmpdir, uploaded_file.name)
                with open(zip_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                with ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                # البحث عن ملف .shp داخل المجلد
                shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
                if shp_files:
                    return gpd.read_file(os.path.join(tmpdir, shp_files[0]))
                else:
                    st.error("لم يتم العثور على ملف .shp داخل الملف المضغوط.")
            elif suffix == '.geojson':
                return gpd.read_file(uploaded_file)
            else:
                st.error("صيغة ملف غير مدعومة. يرجى رفع .zip أو .geojson")
    return None

left_file = st.sidebar.file_uploader("رفع الملف الأساسي (Left)", type=['zip', 'geojson'])
right_file = st.sidebar.file_uploader("رفع الملف الثانوي (Right)", type=['zip', 'geojson'])

# --- المنطقة الرئيسية ---
col1, col2 = st.columns(2)

gdf_left = None
gdf_right = None

if left_file:
    with st.spinner('جاري تحميل الملف الأساسي...'):
        gdf_left = load_data(left_file)
        if gdf_left is not None:
            with col1:
                st.success("تم تحميل الملف الأساسي")
                st.write("أول 5 صفوف:")
                st.dataframe(gdf_left.head())
                st.map(gdf_left)

if right_file:
    with st.spinner('جاري تحميل الملف الثانوي...'):
        gdf_right = load_data(right_file)
        if gdf_right is not None:
            with col2:
                st.success("تم تحميل الملف الثانوي")
                st.write("أول 5 صفوف:")
                st.dataframe(gdf_right.head())
                st.map(gdf_right)

# --- خيارات الربط ---
if gdf_left is not None and gdf_right is not None:
    st.markdown("---")
    st.header("⚙️ إعدادات عملية الربط")

    join_type = st.radio("اختر نوع الربط:", ["ربط مكاني (Spatial Join)", "ربط وصفي (Attribute Join)"])

    result_gdf = None

    if join_type == "ربط مكاني (Spatial Join)":
        predicate = st.selectbox("العلاقة المكانية (Predicate):", ["intersects", "contains", "within", "touches", "crosses"])
        if st.button("تنفيذ الربط المكاني"):
            # التأكد من تطابق نظام الإحداثيات CRS
            if gdf_left.crs != gdf_right.crs:
                gdf_right = gdf_right.to_crs(gdf_left.crs)

            result_gdf = gpd.sjoin(gdf_left, gdf_right, predicate=predicate, how="left")
            st.success("تمت العملية بنجاح!")

    else:  # Attribute Join
        col_l, col_r = st.columns(2)
        left_on = col_l.selectbox("حقل الربط في الملف الأساسي:", gdf_left.columns)
        right_on = col_r.selectbox("حقل الربط في الملف الثانوي:", gdf_right.columns)
        how_attr = st.selectbox("نوع الربط الوصفي:", ["left", "right", "inner", "outer"])

        if st.button("تنفيذ الربط الوصفي"):
            result_gdf = gdf_left.merge(pd.DataFrame(gdf_right.drop(columns='geometry')), left_on=left_on, right_on=right_on, how=how_attr)
            # تحويل النتيجة لـ GeoDataFrame مجدداً
            result_gdf = gpd.GeoDataFrame(result_gdf, geometry='geometry', crs=gdf_left.crs)
            st.success("تمت العملية بنجاح!")

    # --- عرض النتائج والتنزيل ---
    if result_gdf is not None:
        st.markdown("---")
        st.header("📊 النتيجة النهائية")
        st.write(f"عدد الأسطر الناتجة: **{len(result_gdf)}**")

        if len(result_gdf) == 0:
            st.warning("⚠️ لا توجد نتائج مطابقة بناءً على الإعدادات المختارة.")
        else:
            st.dataframe(result_gdf.head())

            # تحويل النتيجة لـ GeoJSON للتنزيل
            geojson_data = result_gdf.to_json()
            st.download_button(
                label="📥 تنزيل النتيجة بصيغة GeoJSON",
                data=geojson_data,
                file_name="joined_data.geojson",
                mime="application/json"
            )
else:
    st.info("يرجى رفع الملفين من القائمة الجانبية للبدء.")