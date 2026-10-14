from __future__ import annotations

import io
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from data_utils import (
    PLANTS,
    analog_similarity_series,
    annual_projection_table,
    comparison_table,
    current_period,
    daily_remaining_production_forecast,
    load_daily_folders,
    load_folder,
    rank_analog_years,
    read_workbook,
)


st.set_page_config(
    page_title="Truy vấn sản lượng và lưu lượng",
    page_icon=":material/water_drop:",
    layout="wide",
)


@st.cache_data(ttl="5m", show_spinner="Đang đọc dữ liệu Excel...")
def load_local_data(folder: str) -> tuple[pd.DataFrame, list[str]]:
    return load_folder(folder)


@st.cache_data(ttl="5m", show_spinner="Đang đọc dữ liệu sản lượng và thủy văn ngày...")
def load_daily_data(folder: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_daily_folders(folder)


@st.cache_data(ttl="5m", show_spinner="Đang đọc tệp đã tải lên...")
def load_uploaded_data(files: tuple[tuple[str, bytes], ...]) -> pd.DataFrame:
    frames = [read_workbook(io.BytesIO(content)) for _, content in files]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    data = pd.concat(frames, ignore_index=True)
    return (
        data.groupby(["year", "month", "plant"], as_index=False)[["production", "flow"]]
        .mean()
        .sort_values(["year", "month", "plant"])
    )


def remember_plant() -> None:
    click = st.session_state.get("analog_click")
    if click is not None:
        st.session_state["selected_plant"] = PLANTS[click["row"]]


st.title("Sản lượng và lưu lượng tháng hiện tại")
st.caption("Dữ liệu được đọc trực tiếp từ Excel. Đơn vị giữ nguyên theo nguồn: sản lượng triệu kWh, lưu lượng m³/s.")

local_data, local_files = load_local_data(str(Path.cwd()))
daily_production, daily_hydrology = load_daily_data(str(Path.cwd()))
cutoff_path = Path.cwd() / "data_cutoff.txt"
data_as_of = None
if not daily_production.empty and not daily_hydrology.empty:
    complete_production_dates = set(
        daily_production.groupby("date")["plant"].nunique().loc[lambda values: values >= len(PLANTS)].index
    )
    complete_hydrology_dates = set(
        daily_hydrology.groupby("date")["plant"].nunique().loc[lambda values: values >= len(PLANTS)].index
    )
    common_dates = complete_production_dates & complete_hydrology_dates
    if common_dates:
        data_as_of = pd.Timestamp(max(common_dates))
elif cutoff_path.exists():
    try:
        data_as_of = pd.Timestamp(cutoff_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        data_as_of = None

with st.sidebar:
    st.header("Nguồn dữ liệu")
    uploads = st.file_uploader(
        "Chọn Excel nếu tệp chưa nằm trong thư mục",
        type=["xlsx", "xls", "xlsm"],
        accept_multiple_files=True,
        help="Ứng dụng tự nhận dạng bảng dài hoặc workbook có mỗi sheet là một năm.",
    )
    if st.button(":material/refresh: Đọc lại dữ liệu", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    if local_files:
        st.success(f"Đã đọc {len(local_files)} tệp trong thư mục.")
        for name in local_files:
            st.caption(name)

uploaded_data = pd.DataFrame()
if uploads:
    uploaded_data = load_uploaded_data(tuple((file.name, file.getvalue()) for file in uploads))

data = pd.concat([local_data, uploaded_data], ignore_index=True) if not local_data.empty or not uploaded_data.empty else pd.DataFrame()
if not data.empty:
    data = (
        data.groupby(["year", "month", "plant"], as_index=False)[["production", "flow"]]
        .mean()
        .sort_values(["year", "month", "plant"])
    )

if data_as_of is not None and not daily_production.empty and not daily_hydrology.empty:
    current_daily_production = daily_production[
        (daily_production["date"].dt.year == data_as_of.year)
        & (daily_production["date"].dt.month == data_as_of.month)
        & (daily_production["date"] <= data_as_of)
    ]
    current_daily_hydrology = daily_hydrology[
        (daily_hydrology["date"].dt.year == data_as_of.year)
        & (daily_hydrology["date"].dt.month == data_as_of.month)
        & (daily_hydrology["date"] <= data_as_of)
    ]
    current_rows = []
    for plant in PLANTS:
        plant_production = current_daily_production[
            current_daily_production["plant"] == plant
        ]["production"]
        plant_flow = current_daily_hydrology[current_daily_hydrology["plant"] == plant]["flow"]
        current_rows.append(
            {
                "year": data_as_of.year,
                "month": data_as_of.month,
                "plant": plant,
                "production": plant_production.sum(min_count=1),
                "flow": plant_flow.mean(),
            }
        )
    current_actuals = pd.DataFrame(current_rows)
    same_period = (data["year"] == data_as_of.year) & (data["month"] == data_as_of.month)
    data = pd.concat([data.loc[~same_period], current_actuals], ignore_index=True).sort_values(
        ["year", "month", "plant"]
    )

if data.empty:
    st.info(
        "Chưa tìm thấy dữ liệu phù hợp. Hãy đặt file Excel vào cùng thư mục với `streamlit_app.py` "
        "hoặc chọn file ở thanh bên."
    )
    st.markdown(
        "**Định dạng được hỗ trợ:** bảng có các cột Năm, Tháng, Nhà máy, Sản lượng, Lưu lượng; "
        "hoặc workbook có các sheet mang tên năm và 12 cột tháng."
    )
    st.stop()

year, month, is_calendar_current = current_period(data)
is_partial_month = bool(
    data_as_of is not None
    and data_as_of.year == year
    and data_as_of.month == month
    and data_as_of.day < data_as_of.days_in_month
)
analog_month = month - 1 if is_partial_month and month > 1 else month
if data_as_of is not None and data_as_of.year == year and data_as_of.month == month:
    st.success(f"Dữ liệu thực tế cập nhật đến ngày {data_as_of.strftime('%d/%m/%Y')}.")
elif not is_calendar_current:
    st.warning(
        f"Excel chưa có dữ liệu cho tháng hiện tại. Trang đang hiển thị kỳ mới nhất tìm thấy: tháng {month}/{year}."
    )
else:
    st.success(f"Kỳ dữ liệu hiện tại: tháng {month}/{year}")

period = data[(data["year"] == year) & (data["month"] == month)].set_index("plant")
summary_rows: list[dict[str, object]] = []
best_by_plant: dict[str, int | None] = {}
for plant in PLANTS:
    ranked = rank_analog_years(data, year, analog_month, plant)
    analog_year = int(ranked.iloc[0]["year"]) if not ranked.empty else None
    best_by_plant[plant] = analog_year
    summary_rows.append(
        {
            "Nhà máy": plant,
            "Sản lượng tháng hiện tại": period.at[plant, "production"] if plant in period.index else None,
            "Lưu lượng hiện tại": period.at[plant, "flow"] if plant in period.index else None,
            "Năm đồng dạng / Truy vấn": (
                f":material/search: {analog_year} · Xem" if analog_year else "Chưa đủ dữ liệu"
            ),
        }
    )

summary = pd.DataFrame(summary_rows)
st.subheader(f"Tổng hợp tháng {month}/{year}")
st.dataframe(
    summary,
    hide_index=True,
    row_height=48,
    column_config={
        "Nhà máy": st.column_config.TextColumn("Nhà máy", pinned=True, width="medium"),
        "Sản lượng tháng hiện tại": st.column_config.NumberColumn(
            "Sản lượng tháng hiện tại (triệu kWh)", format="%.3f", width="medium"
        ),
        "Lưu lượng hiện tại": st.column_config.NumberColumn(
            "Lưu lượng hiện tại (m³/s)", format="%.3f", width="medium"
        ),
        "Năm đồng dạng / Truy vấn": st.column_config.ButtonColumn(
            "Năm đồng dạng / Truy vấn",
            type="primary",
            on_click=remember_plant,
            key="analog_click",
            width="medium",
        ),
    },
)

with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center"):
    if st.button(":material/query_stats: Truy vấn cả 3 nhà máy", type="primary"):
        st.session_state["selected_plant"] = "Tất cả"
    st.caption(
        f"Năm đồng dạng được xác định từ quy luật sản lượng và lưu lượng tháng 1–{analog_month}; "
        "năm lịch sử thiếu dữ liệu trong giai đoạn này sẽ không được xếp hạng."
    )

st.subheader(f"So sánh mức tương đồng đến tháng {analog_month}")
chart_columns = st.columns(3, gap="medium")
for chart_column, plant in zip(chart_columns, PLANTS):
    ranking = rank_analog_years(data, year, analog_month, plant)
    with chart_column.container(border=True, height="stretch"):
        st.markdown(f"**{plant}**")
        if ranking.empty:
            st.info("Chưa đủ dữ liệu để so sánh.")
            continue
        analog_year = int(ranking.iloc[0]["year"])
        similarity = float(ranking.iloc[0]["similarity"])
        st.metric(
            f"{year} so với {analog_year}",
            f"{similarity:.1%}",
            border=False,
        )
        chart_data = analog_similarity_series(
            data, year, analog_month, plant, analog_year
        )
        similarity_chart = (
            alt.Chart(chart_data)
            .mark_line(point=True, strokeWidth=2.5)
            .encode(
                x=alt.X(
                    "Tháng:O",
                    title="Tháng",
                    axis=alt.Axis(labelAngle=0),
                ),
                y=alt.Y(
                    "Chỉ số tương đồng:Q",
                    title="Chỉ số chuẩn hóa",
                    scale=alt.Scale(zero=False),
                ),
                color=alt.Color(
                    "Năm:N",
                    title=None,
                    scale=alt.Scale(
                        domain=[str(year), str(analog_year)],
                        range=["#0b78a5", "#e45756"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("Năm:N"),
                    alt.Tooltip("Tháng:O"),
                    alt.Tooltip("Chỉ số tương đồng:Q", format=".1f"),
                ],
            )
            .properties(height=230)
        )
        st.altair_chart(similarity_chart)
st.caption(
    "Chỉ số chuẩn hóa kết hợp sản lượng và lưu lượng; mức 100 tương ứng với bình quân "
    f"của năm {year} trong giai đoạn T1–T{analog_month}. Hai đường càng gần nhau thì quy luật càng tương đồng."
)

selected = st.session_state.get("selected_plant")
if selected:
    plant_filter = None if selected == "Tất cả" else selected
    ranking = rank_analog_years(data, year, analog_month, plant_filter)
    title = "cả 3 nhà máy" if plant_filter is None else plant_filter
    st.divider()
    st.subheader(f"Kết quả năm đồng dạng tháng 1–{analog_month} — {title}")
    if ranking.empty:
        st.warning("Chưa đủ dữ liệu lịch sử từ tháng 1 đến kỳ hiện tại để xác định năm đồng dạng.")
    else:
        analog_year = int(ranking.iloc[0]["year"])
        similarity = float(ranking.iloc[0]["similarity"])
        with st.container(horizontal=True):
            st.metric("Năm đồng dạng nhất", str(analog_year), border=True)
            st.metric("Mức tương đồng", f"{similarity:.1%}", border=True)
            st.metric("Số điểm dữ liệu so sánh", str(int(ranking.iloc[0]["comparisons"])), border=True)

        details = comparison_table(data, year, analog_month, analog_year, plant_filter)
        detail_columns = {
            column: st.column_config.NumberColumn(column, format="%.3f")
            for column in details.columns
            if column not in {"Nhà máy", "Tháng"}
        }
        detail_columns["Tháng"] = st.column_config.NumberColumn(
            "Tháng", format="%d", width="small"
        )
        st.dataframe(
            details,
            hide_index=True,
            column_config=detail_columns,
        )
        with st.expander("Xem xếp hạng các năm lịch sử"):
            display_ranking = ranking.rename(
                columns={
                    "year": "Năm",
                    "score": "Sai lệch bình quân",
                    "similarity": "Mức tương đồng",
                    "comparisons": "Số điểm dữ liệu",
                }
            )
            st.dataframe(
                display_ranking,
                hide_index=True,
                column_config={
                    "Năm": st.column_config.NumberColumn(format="%d"),
                    "Sai lệch bình quân": st.column_config.NumberColumn(format="percent"),
                    "Mức tương đồng": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
                },
            )

st.divider()
st.subheader(f"Dự kiến sản lượng còn lại năm {year}")
projection = annual_projection_table(data, year, month, data_as_of, daily_production)
forecast_columns = [f"T{forecast_month}" for forecast_month in range(month + 1, 13)]

if is_partial_month and data_as_of is not None:
    projection_by_plant = projection.set_index("Nhà máy")
    current_month = data[(data["year"] == year) & (data["month"] == month)].set_index("plant")
    remainder_rows = []
    for plant in PLANTS:
        actual_value = (
            float(current_month.at[plant, "production"])
            if plant in current_month.index and pd.notna(current_month.at[plant, "production"])
            else float("nan")
        )
        projected_month = float(projection_by_plant.at[plant, f"T{month}"])
        later_months = sum(
            float(projection_by_plant.at[plant, f"T{future_month}"])
            for future_month in range(month + 1, 13)
        )
        remainder_rows.append(
            {
                "Nhà máy": plant,
                f"Thực tế 1–{data_as_of.day}/{month}": actual_value,
                f"Dự kiến {data_as_of.day + 1}–{data_as_of.days_in_month}/{month}": projected_month - actual_value,
                f"Dự kiến T{month}": projected_month,
                "Dự kiến các tháng sau": later_months,
                f"Sản lượng còn lại {year}": projected_month - actual_value + later_months,
                f"Dự kiến cả năm {year}": float(projection_by_plant.at[plant, "Tổng năm"]),
            }
        )
    remainder = pd.DataFrame(remainder_rows)
    st.dataframe(
        remainder,
        hide_index=True,
        row_height=42,
        column_config={
            "Nhà máy": st.column_config.TextColumn(pinned=True, width="medium"),
            **{
                column: st.column_config.NumberColumn(column, format="%.3f", width="medium")
                for column in remainder.columns
                if column != "Nhà máy"
            },
        },
    )
    st.caption(
        f"Đơn vị: triệu kWh. Phần còn lại của tháng {month} được cộng theo sản lượng "
        "từng ngày tương ứng của năm đồng dạng."
    )
    daily_forecast = daily_remaining_production_forecast(
        data, daily_production, year, month, data_as_of
    )
    if not daily_forecast.empty:
        with st.expander("Xem dự kiến từng ngày còn lại trong tháng"):
            st.dataframe(
                daily_forecast,
                hide_index=True,
                column_config={
                    "Ngày dự kiến": st.column_config.DateColumn(format="DD/MM/YYYY"),
                    "Năm quy luật": st.column_config.NumberColumn(format="%d"),
                    "Sản lượng dự kiến": st.column_config.NumberColumn(
                        "Sản lượng dự kiến (triệu kWh)", format="%.3f"
                    ),
                },
            )

st.markdown("**Bảng sản lượng theo tháng**")


def style_projection(frame: pd.DataFrame) -> pd.DataFrame:
    styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
    total_mask = frame["Nhà máy"].eq("Tổng cộng")
    if forecast_columns:
        styles.loc[~total_mask, forecast_columns] = (
            "color: #c62828; background-color: #fff1f1; font-weight: 600"
        )
    if is_partial_month:
        styles.loc[~total_mask, f"T{month}"] = (
            "color: #8a5200; background-color: #fff4d6; font-weight: 600"
        )
    styles.loc[total_mask, :] = "background-color: #eaf2f7; font-weight: 700"
    return styles


projection_columns = {
    "Nhà máy": st.column_config.TextColumn("Nhà máy", pinned=True, width="medium"),
    "Năm quy luật": st.column_config.NumberColumn("Năm quy luật", format="%d", width="small"),
    "Tổng năm": st.column_config.NumberColumn("Tổng năm", format="%.1f", width="small"),
}
projection_columns.update(
    {
        f"T{projection_month}": st.column_config.NumberColumn(
            f"T{projection_month}", format="%.1f", width="small"
        )
        for projection_month in range(1, 13)
    }
)

st.dataframe(
    projection.style.apply(style_projection, axis=None),
    hide_index=True,
    row_height=42,
    column_config=projection_columns,
)
with st.container(horizontal=True, horizontal_alignment="left"):
    actual_end_month = month - 1 if is_partial_month else month
    st.caption(f"🔵 Thực tế: sản lượng {year} từ T1 đến T{actual_end_month}")
    if is_partial_month and data_as_of is not None:
        st.caption(
            f"🟠 T{month}: thực tế đến {data_as_of.day}/{month} + phần còn lại theo năm quy luật"
        )
    if forecast_columns:
        st.caption(
            f"🔴 Dự kiến: sản lượng năm quy luật từ T{month + 1} đến T12"
        )
if is_partial_month:
    st.info(
        f"Sản lượng và lưu lượng hiện tại được tổng hợp từ dữ liệu ngày đến "
        f"{data_as_of.strftime('%d/%m/%Y')}. Năm đồng dạng dùng dữ liệu các tháng đầy đủ "
        f"T1–T{analog_month}; dự kiến phần còn lại của T{month} lấy từng ngày của năm đồng dạng."
    )
