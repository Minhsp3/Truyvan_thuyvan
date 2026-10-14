import os
import re
import sys
import json
from pathlib import Path
from urllib.parse import urlencode, unquote, urlparse, parse_qs
from datetime import datetime

import pandas as pd
import requests
import urllib3

# ============================================================
# CAU HINH
# ============================================================

BASE_URL = "https://bcqt.evn.com.vn"
SITE = "PMIS"
WORKBOOK = "1_Tnhhnhsnxut_16004096889310"
VIEW = "1_2_Snlnginsnxut"
TABLEAU_VERSION = "2026.2"
PARAMETER_NAME = "[Parameters].[Parameter 2 1]"
SHEETDOC_ID = "{2445E0E9-8E43-420E-A366-837C16A4CF6C}"

VIZQL_SESSION_ID = os.getenv(
    "EVN_VIZQL_SESSION_ID",
    "11CA072EAFF4441A9F2D3BC1BA1E6DAB-1:0",
)

WORKGROUP_SESSION_ID = os.getenv(
    "EVN_WORKGROUP_SESSION_ID",
    "md5Q1QJfQumcTKGmrJjqgA|v7XZnMsd2N46eoxcvGncugwJDIkOAqnf|e70cc617-b04e-4a47-bfb6-39269ae42d4a",
)

XSRF_TOKEN = os.getenv(
    "EVN_XSRF_TOKEN",
    "Bxu27uJH0QMLE5ItLJb9iMq5Cdto2bOw",
)

# Neu phien dang nhap cua ban can cookie nay thi dat Environment Variable.
PHAPDIEN_SHARE_AUTH = os.getenv("EVN_PHAPDIEN_SHARE_AUTH", "")

# He thong noi bo co the dung chuoi CA ma Python khong tin cay mac dinh.
# Dat False de test. Ve lau dai nen cau hinh CA noi bo va dat True.
VERIFY_SSL = False

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GENCO3_PLANTS = [
    "Phú Mỹ 1",
    "Phú Mỹ 3",
    "Phú Mỹ 4",
    "Phú Mỹ 21",
    "Phú Mỹ 22",
    "Vĩnh Tân 2",
    "Buôn Kuop",
    "Buôn Tua Srah",
    "Srepok 3",
    "Bà Rịa",
    "Ninh Bình",
]


class EVNTableauClient:
    def __init__(self, vizql_session_id, workgroup_session_id, xsrf_token):
        self.vizql_session_id = vizql_session_id
        self.workgroup_session_id = workgroup_session_id
        self.xsrf_token = xsrf_token

        self.session = requests.Session()
        self.session.verify = VERIFY_SSL

        self.referer = (
            f"{BASE_URL}/t/{SITE}/views/{WORKBOOK}/{VIEW}"
            "?%3Aembed=y"
            "&%3AshowVizHome=n"
            "&%3Atoolbar=top"
        )

        cookies = {
            "workgroup_session_id": self.workgroup_session_id,
            "XSRF-TOKEN": self.xsrf_token,
            "tableau_locale": "en-GB",
        }
        if PHAPDIEN_SHARE_AUTH:
            cookies["PhapDienShareAuth"] = PHAPDIEN_SHARE_AUTH

        self.session.cookies.update(cookies)

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/153.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
                "Origin": BASE_URL,
                "Referer": self.referer,
                "X-Requested-With": "XMLHttpRequest",
                "X-Tableau-Version": TABLEAU_VERSION,
                "X-XSRF-TOKEN": self.xsrf_token,
            }
        )

    def session_base_url(self):
        return (
            f"{BASE_URL}/vizql/t/{SITE}/"
            f"w/{WORKBOOK}/"
            f"v/{VIEW}/"
            f"sessions/{self.vizql_session_id}"
        )

    @staticmethod
    def _raise_tableau_error(response, action):
        if response.status_code == 401:
            raise RuntimeError(
                f"{action}: HTTP 401 - cookie/phien dang nhap khong con hop le."
            )
        if response.status_code == 403:
            raise RuntimeError(
                f"{action}: HTTP 403 - XSRF token hoac quyen truy cap khong hop le/het han."
            )
        if response.status_code == 404:
            raise RuntimeError(
                f"{action}: HTTP 404 - VIZQL_SESSION_ID co kha nang da het han. "
                "Mo lai dashboard va lay session ID moi tu Network."
            )
        response.raise_for_status()

    def set_date(self, date_string):
        url = self.session_base_url() + "/commands/tabdoc/set-parameter-value"

        files = {
            "globalFieldName": (None, PARAMETER_NAME),
            "valueString": (None, date_string),
            "useUsLocale": (None, "false"),
            "telemetryCommandId": (None, "python-evnbi"),
        }

        print("\n" + "=" * 70)
        print("DANG DOI NGAY DASHBOARD")
        print("=" * 70)
        print("Ngay yeu cau:", date_string)

        try:
            response = self.session.post(
                url,
                headers={"Accept": "text/javascript"},
                files=files,
                timeout=60,
            )
        except requests.exceptions.SSLError as exc:
            raise RuntimeError(
                "Loi SSL. Dat VERIFY_SSL = False de test hoac cau hinh CA noi bo."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Khong ket noi duoc EVNBI: {exc}") from exc

        print("HTTP:", response.status_code)
        print("Dung luong response:", len(response.content), "bytes")
        print("Content-Type:", response.headers.get("Content-Type"))

        self._raise_tableau_error(response, "set_date")
        self.verify_selected_date(response, date_string)
        return response

    @staticmethod
    def verify_selected_date(response, expected_date):
        """Xac nhan response Tableau da chuyen sang dung ngay."""
        expected_iso = datetime.strptime(expected_date, "%d/%m/%Y").strftime("%Y-%m-%d")
        text = response.text

        # Response Tableau thuong co cac truong nhu:
        # formattedValue: "18/09/2026"
        # unformattedValue: "18/09/2026"
        # valueAlias: ["2026-09-18", ""]
        checks = [
            expected_date in text,
            expected_iso in text,
            f'"formattedValue": "{expected_date}"' in text,
            f'"unformattedValue": "{expected_date}"' in text,
        ]

        if any(checks):
            print(f"OK - Tableau da xac nhan ngay {expected_date}.")
            return True

        preview_file = Path("set_parameter_response_unverified.txt")
        preview_file.write_text(text, encoding="utf-8", errors="ignore")
        raise RuntimeError(
            "Tableau tra HTTP thanh cong nhung response khong xac nhan dung ngay "
            f"{expected_date}. Da luu response tai: {preview_file.resolve()}"
        )

    @staticmethod
    def save_parameter_response(response, date_string):
        safe_date = date_string.replace("/", "-")
        filename = Path(f"set_parameter_response_{safe_date}.txt")
        filename.write_text(response.text, encoding="utf-8", errors="ignore")
        print("Da luu response:", filename.resolve())

    def download_tempfile(self, tempfile_key, output_dir="downloads"):
        query = urlencode(
            {
                "key": tempfile_key,
                "keepfile": "yes",
                "attachment": "yes",
            }
        )

        url = (
            f"{BASE_URL}/vizql/t/{SITE}/"
            f"w/{WORKBOOK}/"
            f"v/{VIEW}/"
            f"tempfile/sessions/{self.vizql_session_id}?{query}"
        )

        print("\n" + "=" * 70)
        print("DANG TAI FILE TABLEAU")
        print("=" * 70)
        print("Tempfile key MOI:", tempfile_key)

        try:
            response = self.session.get(
                url,
                headers={"Accept": "*/*"},
                timeout=120,
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Khong tai duoc tempfile: {exc}") from exc

        print("HTTP:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Content-Disposition:", response.headers.get("Content-Disposition"))
        print("Dung luong:", len(response.content), "bytes")

        self._raise_tableau_error(response, "download_tempfile")

        content_type = (response.headers.get("Content-Type") or "").lower()
        if "text/html" in content_type and len(response.content) < 2_000_000:
            preview = response.text[:500].replace("\n", " ")
            raise RuntimeError(
                "Server tra HTML thay vi file export. Key co the cu/het han hoac session "
                f"khong con hop le. Preview: {preview}"
            )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = self.detect_filename(response)
        filepath = output_dir / filename
        filepath.write_bytes(response.content)

        print("Da tai:", filepath.resolve())
        return filepath


    def open_export_crosstab_dialog(self):
        """
        Goi lenh Tableau mo hop thoai Export Crosstab sau khi da set ngay.
        Request nay co the chi tra ve metadata cua dialog; neu response da chua
        tempfile URL/key thi ham se tu dong tach key.
        """
        url = self.session_base_url() + "/commands/tabsrv/export-crosstab-server-dialog"

        thumbnail_uris = {
            "1.1. Công suất toàn hệ thống": f"/t/{SITE}/thumb/views/{WORKBOOK}/1_1_Cngsuttonhthng",
            "1.2. Sản lượng điện sản xuất ": f"/t/{SITE}/thumb/views/{WORKBOOK}/{VIEW}",
            "1.3. Phương thức": f"/t/{SITE}/thumb/views/{WORKBOOK}/1_3_Phngthc",
            "1.4. Cân bằng nguồn": f"/t/{SITE}/thumb/views/{WORKBOOK}/1_4_Cnbngngun",
        }

        files = {
            "thumbnailUris": (
                None,
                json.dumps(thumbnail_uris, ensure_ascii=False, separators=(",", ":")),
            ),
            "telemetryCommandId": (None, "python-export-crosstab-dialog"),
        }

        print("\n" + "=" * 70)
        print("MO HOP THOAI EXPORT CROSSTAB")
        print("=" * 70)

        try:
            response = self.session.post(
                url,
                headers={"Accept": "text/javascript"},
                files=files,
                timeout=60,
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Khong goi duoc export-crosstab dialog: {exc}") from exc

        print("HTTP:", response.status_code)
        print("Dung luong response:", len(response.content), "bytes")
        print("Content-Type:", response.headers.get("Content-Type"))
        self._raise_tableau_error(response, "export_crosstab_server_dialog")

        out = Path("export_crosstab_dialog_response.txt")
        out.write_text(response.text, encoding="utf-8", errors="ignore")
        print("Da luu response dialog:", out.resolve())

        key = self.extract_tempfile_key_from_text(response.text)
        if key:
            print("Da tim thay tempfile key trong response dialog:", key)
        else:
            print(
                "Response dialog chua co tempfile key. "
                "Dieu nay cho thay lenh nay chi mo hop thoai; "
                "can request xuat file sau khi bam Download trong dialog."
            )

        return response, key

    @staticmethod
    def extract_tempfile_key_from_text(text):
        """Tach tempfile key tu response Tableau 2026.2.

        Uu tien cau truc JSON thuc te:
        vqlCmdResponse -> layoutStatus -> applicationPresModel ->
        presentationLayerNotification[] -> presModelHolder ->
        genExportFilePresModel -> resultKey
        """
        if not text:
            return None

        try:
            payload = json.loads(text)
            notifications = (
                payload.get("vqlCmdResponse", {})
                .get("layoutStatus", {})
                .get("applicationPresModel", {})
                .get("presentationLayerNotification", [])
            )
            for item in notifications:
                model = (
                    item.get("presModelHolder", {})
                    .get("genExportFilePresModel", {})
                )
                result_key = model.get("resultKey")
                if result_key is not None:
                    return str(result_key)
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

        patterns = [
            r'"resultKey"\s*:\s*"?([A-Za-z0-9._:-]+)',
            r"/tempfile/sessions/[^?\"']+\?[^\"']*?key=([A-Za-z0-9._:-]+)",
            r"(?:\?|&|\\u0026)key=([A-Za-z0-9._:-]+)",
            r'"key"\s*:\s*"?([A-Za-z0-9._:-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return match.group(1)
        return None

    def export_crosstab_to_csvserver(self, sheetdoc_id=SHEETDOC_ID):
        """
        Tao file Crosstab/CSV moi tu trang thai dashboard hien tai.
        Day la request ma trinh duyet gui ngay truoc tempfile download.
        Ham tra ve (response, tempfile_key).
        """
        url = self.session_base_url() + "/commands/tabsrv/export-crosstab-to-csvserver"

        files = {
            "sheetdocId": (None, sheetdoc_id),
            "useTabs": (None, "true"),
            "sendNotifications": (None, "true"),
            "telemetryCommandId": (None, "python-export-crosstab-csv"),
        }

        print("\n" + "=" * 70)
        print("TAO FILE EXPORT CROSSTAB MOI")
        print("=" * 70)
        print("sheetdocId:", sheetdoc_id)

        try:
            response = self.session.post(
                url,
                headers={"Accept": "text/javascript"},
                files=files,
                timeout=120,
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Khong tao duoc crosstab export: {exc}") from exc

        print("HTTP:", response.status_code)
        print("Dung luong response:", len(response.content), "bytes")
        print("Content-Type:", response.headers.get("Content-Type"))
        self._raise_tableau_error(response, "export_crosstab_to_csvserver")

        out = Path("export_crosstab_to_csvserver_response.txt")
        out.write_text(response.text, encoding="utf-8", errors="ignore")
        print("Da luu response export:", out.resolve())

        # Doc metadata file export tu response Tableau.
        try:
            payload = response.json()
            notifications = (
                payload.get("vqlCmdResponse", {})
                .get("layoutStatus", {})
                .get("applicationPresModel", {})
                .get("presentationLayerNotification", [])
            )
            for item in notifications:
                model = (
                    item.get("presModelHolder", {})
                    .get("genExportFilePresModel", {})
                )
                if model:
                    print("File export:", model.get("fileName"))
                    print("MIME type:", model.get("mimeType"))
                    print("Result key:", model.get("resultKey"))
                    break
        except Exception:
            pass

        key = self.extract_tempfile_key_from_text(response.text)

        # Mot so response Tableau co the tra key duoi dang so thuan trong
        # JSON/JS ma khong kem URL. Thu bo sung mot vai pattern chat hon.
        if not key:
            extra_patterns = [
                r'key[=:]\s*["\']?([0-9]{6,})',
                r'tempfile[^0-9]{0,80}([0-9]{6,})',
            ]
            for pattern in extra_patterns:
                match = re.search(pattern, response.text, flags=re.I)
                if match:
                    key = match.group(1)
                    break

        if key:
            print("Da tim thay tempfile key MOI:", key)
        else:
            print("Chua tim thay tempfile key trong response export.")

        return response, key

    @staticmethod
    def detect_filename(response):
        disposition = response.headers.get("Content-Disposition", "")

        match = re.search(r"filename\*=UTF-8''([^;]+)", disposition, flags=re.I)
        if match:
            return unquote(match.group(1))

        match = re.search(r'filename="?([^";]+)"?', disposition, flags=re.I)
        if match:
            return match.group(1).strip()

        content_type = (response.headers.get("Content-Type") or "").lower()
        if "spreadsheetml" in content_type:
            return "san_luong_dien.xlsx"
        if "excel" in content_type:
            return "san_luong_dien.xls"
        if "csv" in content_type:
            return "san_luong_dien.csv"
        if "zip" in content_type:
            return "tableau_export.zip"
        return "tableau_export.bin"


def parse_tempfile_key(value, expected_session_id):
    """
    Nhan 1 trong 2 dang:
      1) key thuan: 1234567890
      2) URL tempfile day du
    Tra ve key; neu URL co session khac thi canh bao.
    """
    value = value.strip()
    if not value:
        raise ValueError("Chua nhap tempfile key/URL moi.")

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        qs = parse_qs(parsed.query)
        keys = qs.get("key")
        if not keys or not keys[0]:
            raise ValueError("URL tempfile khong co tham so key=...")

        match = re.search(r"/tempfile/sessions/([^?]+)", parsed.path)
        if match:
            url_session = unquote(match.group(1))
            if url_session != expected_session_id:
                raise ValueError(
                    "URL tempfile thuoc VIZQL session khac. "
                    f"Code dang dung {expected_session_id}, URL dung {url_session}. "
                    "Hay cap nhat VIZQL_SESSION_ID hoac lay tempfile URL trong cung phien."
                )
        return keys[0]

    # Neu chi dan key, chap nhan chuoi so/chu an toan.
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        raise ValueError("Tempfile key co ky tu khong hop le.")
    return value


def read_export_file(filepath):
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    print("\n" + "=" * 70)
    print("DOC FILE")
    print("=" * 70)
    print("File:", filepath)

    if suffix in (".xlsx", ".xls"):
        excel = pd.ExcelFile(filepath)
        print("Sheets:", excel.sheet_names)
        return pd.read_excel(filepath, sheet_name=excel.sheet_names[0])

    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin1"):
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                print("Doc CSV voi encoding:", encoding)
                return df
            except Exception:
                continue
        raise RuntimeError("Khong doc duoc CSV bang cac encoding thong dung.")

    print("File chua xac dinh duoc dinh dang de dua vao pandas.")
    return None


def inspect_dataframe(df):
    if df is None:
        return

    print("\n" + "=" * 70)
    print("CAU TRUC DU LIEU")
    print("=" * 70)
    print("So dong:", len(df))
    print("So cot:", len(df.columns))
    print("Cac cot:")
    for i, column in enumerate(df.columns, 1):
        print(f"{i:02d}. {column}")
    print("\n5 dong dau:")
    print(df.head().to_string())


def find_plant_column(df):
    candidates = [
        "Công nghệ phát điện",
        " Công nghệ phát điện",
        "Nhà máy",
        "Đơn vị",
        "Tên nhà máy",
    ]

    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    for column in df.columns:
        text = str(column).lower()
        if "công nghệ" in text or "phát điện" in text or "nhà máy" in text:
            return column
    return None


def filter_genco3(df):
    if df is None:
        return None

    plant_column = find_plant_column(df)
    if plant_column is None:
        print("Khong xac dinh duoc cot ten nha may.")
        return None

    print("Cot nha may:", plant_column)

    plant_values = df[plant_column].astype(str).str.strip()
    wanted = {name.strip() for name in GENCO3_PLANTS}
    result = df[plant_values.isin(wanted)].copy()

    print("\n" + "=" * 70)
    print("DU LIEU GENCO3")
    print("=" * 70)
    if result.empty:
        print("Khong tim thay cac nha may GENCO3 trong file export.")
    else:
        print(result.to_string(index=False))
    return result


def export_result(df, filename):
    if df is None or df.empty:
        return
    df.to_excel(filename, index=False)
    print("Da xuat ket qua GENCO3:", Path(filename).resolve())


def check_config():
    missing = []
    if not VIZQL_SESSION_ID or VIZQL_SESSION_ID.startswith("YOUR_"):
        missing.append("VIZQL_SESSION_ID")
    if not WORKGROUP_SESSION_ID or WORKGROUP_SESSION_ID.startswith("YOUR_"):
        missing.append("WORKGROUP_SESSION_ID")
    if not XSRF_TOKEN or XSRF_TOKEN.startswith("YOUR_"):
        missing.append("XSRF_TOKEN")

    if missing:
        print("Thieu cau hinh:")
        for item in missing:
            print(" -", item)
        print("Hay dien session/token hien tai hoac dat Environment Variable.")
        sys.exit(1)


def validate_date(date_string):
    try:
        return datetime.strptime(date_string, "%d/%m/%Y")
    except ValueError as exc:
        raise ValueError("Ngay phai hop le va co dang DD/MM/YYYY.") from exc


def main():
    print("\n" + "=" * 70)
    print("EVNBI - LAY SAN LUONG DIEN THEO NGAY")
    print("=" * 70)

    check_config()

    date_string = input("Nhap ngay DD/MM/YYYY [21/09/2026]: ").strip()
    if not date_string:
        date_string = "21/09/2026"

    try:
        validate_date(date_string)

        client = EVNTableauClient(
            vizql_session_id=VIZQL_SESSION_ID,
            workgroup_session_id=WORKGROUP_SESSION_ID,
            xsrf_token=XSRF_TOKEN,
        )

        # Buoc 1: doi ngay va xac nhan response Tableau da nhan dung ngay.
        response = client.set_date(date_string)
        client.save_parameter_response(response, date_string)

        # Buoc 2: mo hop thoai export de dong bo trang thai/metadata.
        # Khong tai file o buoc nay.
        client.open_export_crosstab_dialog()

        # Buoc 3: goi dung request tao Crosstab/CSV moi.
        # Response nay phai sinh tempfile key moi cho ngay vua chon.
        _, tempfile_key = client.export_crosstab_to_csvserver()

        if not tempfile_key:
            raise RuntimeError(
                "Khong tach duoc tempfile key moi tu response export. "
                "Hay mo file export_crosstab_to_csvserver_response.txt va gui noi dung cho minh."
            )

        # Buoc 4: tai file bang key moi vua duoc Tableau tao.
        filepath = client.download_tempfile(tempfile_key)

        # Buoc 5: doc va loc du lieu.
        df = read_export_file(filepath)
        inspect_dataframe(df)
        result = filter_genco3(df)

        date_filename = date_string.replace("/", "-")
        export_result(result, f"San_luong_GENCO3_{date_filename}.xlsx")

        print("\nHOAN TAT.")
        print(
            "Code da tu dong doi ngay, tao export moi, lay tempfile key moi va tai file. "
            "Khong con dung TEMPFILE_KEY co dinh."
        )

    except Exception as exc:
        print("\n" + "!" * 70)
        print("LOI:", exc)
        print("!" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
