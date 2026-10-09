# Agent Instructions & Workflow Rules

## Mandatory Android APK Build Rule
Every time you make any change to the application code, assets, configurations, or UI:
1. **Remove Old APK Files**:
   Remove any pre-existing APK artifacts:
   ```powershell
   Remove-Item -Path "build\apk\*" -Recurse -Force -ErrorAction SilentlyContinue
   ```
2. **Build Fresh APK**:
   Compile the latest application build:
   ```powershell
   flet build apk --yes --no-rich-output
   ```
3. **Verify Build Output**:
   Ensure `build/apk/leaksee.apk` is generated and report its path and file size to the user.
