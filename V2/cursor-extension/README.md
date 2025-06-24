# Review Gate V2 - Cursor Extension

A powerful Cursor IDE extension that provides interactive popup dialogs with support for text input, image uploads, and speech-to-text functionality. Part of the Review Gate V2 ecosystem for enhanced AI-assisted development workflows.

## Features

### Core Functionality
- Interactive popup dialogs for user feedback and input
- Real-time MCP (Model Context Protocol) integration
- Professional user interface with clean design
- Manual trigger support via keyboard shortcut (Cmd+Shift+R)

### Text Input
- Rich text input with auto-resizing textarea
- Support for multi-line input and formatting
- Clean, responsive input field design
- Orange glow focus states for better visual feedback

### Image Upload System
- Support for multiple image formats (PNG, JPG, JPEG, GIF, BMP, WebP)
- Drag and drop functionality
- Image preview before sending
- Base64 encoding with MIME type detection
- Integration with MCP protocol for sending images to AI agents

### Speech-to-Text Integration
- Local speech recognition using Faster-Whisper AI
- Direct system audio recording via SoX
- Visual feedback states:
  - Microphone icon (ready to record)
  - Stop button (recording in progress)
  - Processing spinner (transcribing speech)
- Automatic text injection into input field
- Error handling and recovery

### Visual Design
- Consistent "Review Gate" title across all dialogs
- Horizontally aligned input controls
- MCP status indicator with real-time updates
- Smooth animations and transitions
- Professional orange accent color scheme

## Installation

### Prerequisites
- Cursor IDE (latest version)
- macOS (tested on macOS 14+)
- SoX audio system (installed via Homebrew)

### Extension Installation
1. Download the `review-gate-v2-2.7.3.vsix` file
2. Open Cursor IDE
3. Press `Cmd+Shift+P` to open command palette
4. Type "Extensions: Install from VSIX"
5. Select the downloaded `.vsix` file
6. Restart Cursor when prompted

### MCP Server Setup
This extension requires the Review Gate V2 MCP server to be configured. See the main project documentation for complete setup instructions.

## Usage

### Manual Trigger
Press `Cmd+Shift+R` in any Cursor workspace to open the Review Gate popup.

### Automatic Trigger
When used with the Review Gate V2 MCP server, popups will automatically appear when Cursor agents request user input.

### Text Input
1. Type your response in the input field
2. Use Shift+Enter for new lines
3. Click send button or press Enter to submit

### Image Upload
1. Click the camera icon next to the input field
2. Select one or more images from your file system
3. Preview images in the chat area
4. Send along with your text response

### Speech-to-Text
1. Click the microphone icon (appears when input field is empty)
2. Icon changes to red stop button - speak clearly
3. Click stop button when finished speaking
4. Orange spinner appears during transcription
5. Transcribed text automatically appears in input field

## Technical Details

### Architecture
- Native Cursor extension using VS Code Extension API
- WebView-based user interface with HTML/CSS/JavaScript
- File-based communication with MCP server via temporary files
- Child process integration for system audio recording

### Audio Recording
- Direct SoX system calls via Node.js child_process
- 16kHz, mono, 16-bit WAV format
- Temporary file storage in `/tmp/` directory
- Automatic cleanup after transcription

### MCP Integration
- Watches for trigger files in `/tmp/review_gate_trigger.json`
- Writes responses to multiple file patterns for reliability
- 5-minute timeout for user responses
- Support for trigger ID-based communication

### File Communication Protocol
- Trigger files: `/tmp/review_gate_trigger*.json`
- Response files: `/tmp/review_gate_response*.json`
- Speech files: `/tmp/review_gate_speech_trigger*.json`
- Acknowledgment files: `/tmp/review_gate_ack*.json`

## Configuration

The extension automatically activates on Cursor startup and monitors for MCP tool calls. No manual configuration is required beyond the initial installation.

### Keyboard Shortcuts
- `Cmd+Shift+R` (macOS) - Manual trigger
- `Ctrl+Shift+R` (Windows/Linux) - Manual trigger

## Development

### Building from Source
```bash
npm install
npm run package
```

### Dependencies
- No external Node.js dependencies for runtime
- Uses native child_process for system integration
- SoX system dependency for audio recording

## Troubleshooting

### Extension Not Loading
- Check that extension is enabled in Cursor Extensions panel
- Restart Cursor completely
- Verify no conflicting extensions

### Popup Not Appearing
- Check MCP server is running and configured
- Verify trigger files are being created in `/tmp/`
- Check browser console for JavaScript errors (F12)

### Speech-to-Text Issues
- Ensure SoX is installed: `brew install sox`
- Check microphone permissions in System Preferences
- Test SoX directly: `sox -d -r 16000 -c 1 test.wav trim 0 3`

### Image Upload Problems
- Verify file format is supported
- Check file size limitations
- Ensure sufficient disk space in `/tmp/`

## Compatibility

- **Cursor IDE**: Latest version recommended
- **Operating System**: macOS 14+ (primary), Windows/Linux (limited testing)
- **MCP Protocol**: Compatible with MCP 1.0+
- **Audio System**: Requires SoX for speech functionality

## License

MIT License - see LICENSE file for details

## Support

For issues, feature requests, or contributions, please visit the main project repository at https://github.com/LakshmanTurlapati/Review-Gate

## Version History

### v2.7.3 (Current)
- Paste images directly from the clipboard into the Review Gate popup
- Drag-and-drop image upload support for an even faster workflow
- Ability to remove individual images before sending a message

### v2.5.1
- Complete speech-to-text implementation with SoX integration
- UI fixes for icon state management and alignment
- Consistent title enforcement
- Removed node-mic-record dependency
- Enhanced error handling and recovery

### v2.3.0
- Image upload functionality with MCP integration
- Multi-format image support
- Image preview system

### v2.0.0
- Basic popup system with file communication protocol
- MCP integration foundation
- Real-time status monitoring

### v1.0.0
- Initial extension release
- Basic text input and response handling