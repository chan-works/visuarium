#!/bin/bash
set -e

APP_NAME="Agent"
DIST_DIR="dist"
VERSION_FILE="VERSION"

echo "=============================="
echo " Visuarium Agent macOS Build"
echo "=============================="

# ── 1. 버전 읽기 + 자동 증가 ──────────────────────────────────────────────
CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
MAJOR=$(echo "$CURRENT" | cut -d. -f1)
MINOR=$(echo "$CURRENT" | cut -d. -f2)
PATCH=$(echo "$CURRENT" | cut -d. -f3)

NEW_PATCH=$((PATCH + 1))
NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"

echo "$NEW_VERSION" > "$VERSION_FILE"
echo "[1/5] 버전: ${CURRENT} → ${NEW_VERSION}"

APP_PATH="${DIST_DIR}/${APP_NAME}.app"
DMG_NAME="${APP_NAME}_v${NEW_VERSION}.dmg"
DMG_PATH="${DIST_DIR}/${DMG_NAME}"

# ── 2. 이전 빌드 정리 ─────────────────────────────────────────────────────
echo "[2/5] 이전 빌드 정리..."
rm -rf build "${APP_PATH}"

# ── 3. PyInstaller 빌드 ───────────────────────────────────────────────────
echo "[3/5] PyInstaller 빌드 중... (버전 ${NEW_VERSION})"
APP_VERSION="$NEW_VERSION" pyinstaller build_mac.spec --noconfirm

if [ ! -d "${APP_PATH}" ]; then
    echo "ERROR: ${APP_PATH} 생성 실패"
    # 빌드 실패 시 버전 롤백
    echo "$CURRENT" > "$VERSION_FILE"
    exit 1
fi
echo "  → ${APP_PATH} 생성 완료"

# ── 4. DMG 생성 ───────────────────────────────────────────────────────────
echo "[4/5] DMG 생성 중... (${DMG_NAME})"

TMP_DIR=$(mktemp -d)
cp -R "${APP_PATH}" "${TMP_DIR}/"
ln -s /Applications "${TMP_DIR}/Applications"

hdiutil create \
    -volname "${APP_NAME} ${NEW_VERSION}" \
    -srcfolder "${TMP_DIR}" \
    -ov \
    -format UDZO \
    "${DMG_PATH}"

rm -rf "${TMP_DIR}"
echo "  → ${DMG_PATH} 생성 완료"

# ── 5. 결과 ──────────────────────────────────────────────────────────────
echo "[5/5] 완료!"
ls -lh "${DMG_PATH}"
echo ""
echo "DMG 위치: $(pwd)/${DMG_PATH}"
echo "버전:     ${NEW_VERSION}"
echo ""
echo "dist/ 폴더의 모든 DMG:"
ls -lh dist/*.dmg 2>/dev/null || echo "  (없음)"

open dist/
