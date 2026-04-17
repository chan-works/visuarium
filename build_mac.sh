#!/bin/bash
set -e

APP_NAME="Agent"
DIST_DIR="dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
DMG_PATH="${DIST_DIR}/${APP_NAME}.dmg"
VOLUME_NAME="${APP_NAME}"

echo "=============================="
echo " Visuarium Agent macOS Build"
echo "=============================="

# 1. 이전 빌드 정리
echo "[1/4] 이전 빌드 정리..."
rm -rf build "${DMG_PATH}"

# 2. PyInstaller 빌드
echo "[2/4] PyInstaller 빌드 중..."
pyinstaller build_mac.spec --noconfirm

if [ ! -d "${APP_PATH}" ]; then
    echo "ERROR: ${APP_PATH} 생성 실패"
    exit 1
fi
echo "  → ${APP_PATH} 생성 완료"

# 3. DMG 생성
echo "[3/4] DMG 생성 중..."

# 임시 DMG 디렉토리
TMP_DIR=$(mktemp -d)
cp -R "${APP_PATH}" "${TMP_DIR}/"
ln -s /Applications "${TMP_DIR}/Applications"

hdiutil create \
    -volname "${VOLUME_NAME}" \
    -srcfolder "${TMP_DIR}" \
    -ov \
    -format UDZO \
    "${DMG_PATH}"

rm -rf "${TMP_DIR}"

echo "  → ${DMG_PATH} 생성 완료"

# 4. 결과
echo "[4/4] 완료!"
ls -lh "${DMG_PATH}"
echo ""
echo "DMG 위치: $(pwd)/${DMG_PATH}"
