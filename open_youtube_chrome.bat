@echo off
title DANG NHAP YOUTUBE - HIGHLIGHT VIDEO STUDIO
echo ===================================================================
echo   CHROME PROFILE LOCAL - HIGHLIGHT VIDEO STUDIO
echo ===================================================================
echo Thu muc Profile: %~dp0chrome_profile
echo.
echo Dang mo Google Chrome voi Profile rieng cua app...
echo Vui long dang nhap tai khoan Google / YouTube vao cua so Chrome nay.
echo Sau khi dang nhap xong, hay dong trinh duyet Chrome lai.
echo yt-dlp se tu dong lay live cookies truc tiep tu profile nay moi khi can fallback!
echo ===================================================================
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%~dp0chrome_profile" https://www.youtube.com
