function syncYouTubeMetadata() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Get the Google Sheet DOCUMENT (not tab) name for job number extraction
  const docName = SpreadsheetApp.getActiveSpreadsheet().getName();
  const jobNumberRegex = /([0-9]{4,})(?:L)?-/;
  const match = docName.match(jobNumberRegex);
  let jobNumber = '';
  if (match) {
    jobNumber = match[1]; // This preserves leading zeros!
  }

  const data = sheet.getDataRange().getValues();
  const header = data[0];
  let updatedCount = 0;
  let mismatchCount = 0;
  let errorCount = 0;
  // Column indices (update if your header changes!)
  const col = {
    researcher: header.indexOf('Researcher Name'),
    jobNumber: header.indexOf('Job Number'),
    source: header.indexOf('Source'),
    user: header.indexOf('User'),
    url: header.indexOf('URL'),
    title: header.indexOf('Title'),
    date: header.indexOf('date'),
    duration: header.indexOf('duration'),
    notes: header.indexOf('Researcher Notes')
  };

  // Helper to extract video ID from YouTube URL
  function extractVideoId(url) {
    const regex = /(?:v=|\/)([0-9A-Za-z_-]{11})/;
    const match = url ? url.match(regex) : null;
    return match ? match[1] : null;
  }

  // NEW: Normalize ISO 8601 duration to hh:mm:ss or mm:ss
  function normalizeDuration(isoDuration) {
    const regex = /PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/;
    const match = isoDuration ? isoDuration.match(regex) : null;
    if (!match) return '';
    let hours = parseInt(match[1] || 0, 10);
    let minutes = parseInt(match[2] || 0, 10);
    let seconds = parseInt(match[3] || 0, 10);
    const pad = (num) => num.toString().padStart(2, '0');
    if (hours > 0) {
      return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    } else {
      return `${pad(minutes)}:${pad(seconds)}`;
    }
  }

  function durationToSeconds(durationStr) {
    if (!durationStr) return 0;
    durationStr = String(durationStr);
    // If ISO format
    if (durationStr.startsWith('PT')) {
      const regex = /PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/;
      const match = durationStr.match(regex);
      if (!match) return 0;
      let hours = parseInt(match[1] || 0, 10);
      let minutes = parseInt(match[2] || 0, 10);
      let seconds = parseInt(match[3] || 0, 10);
      return hours * 3600 + minutes * 60 + seconds;
    }
    // If hh:mm:ss or mm:ss
    const parts = durationStr.split(':').map(Number);
    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    }
    // Try as number (seconds)
    if (!isNaN(durationStr)) return Number(durationStr);
    return 0;
  }

  // First, build a map of all YouTube IDs to track duplicates
  const videoIdMap = {};
  for (let i = 1; i < data.length; i++) {
    const url = data[i][col.url];
    const videoId = extractVideoId(url);
    if (videoId) {
      if (!videoIdMap[videoId]) videoIdMap[videoId] = [];
      videoIdMap[videoId].push(i);
    }
  }

  // Now, process each row
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const url = row[col.url];
    const title = row[col.title];
    const notes = [];
    const videoId = extractVideoId(url);

    // 1. Skip empty rows or flagged instruction rows
    if (!url || title === "If clip ID is found, search PWC Archive tab for further data.") {
      continue;
    }

    // 2. Fill 'Job Number' from extracted job number if not present or wrong
    if (col.jobNumber >= 0 && jobNumber && row[col.jobNumber] !== jobNumber) {
      sheet.getRange(i + 1, col.jobNumber + 1).setValue(jobNumber);
    }

    // 3. Fill 'Source' as 'yt'
    if (col.source >= 0 && row[col.source] !== 'yt') {
      sheet.getRange(i + 1, col.source + 1).setValue('yt');
    }

    // 4. Check for duplicate video IDs and color all URL cells orange if found
    if (videoId && videoIdMap[videoId].length > 1) {
      sheet.getRange(i + 1, col.url + 1).setBackground('orange');
      notes.push(`⛔ Duplicate ID (also in rows: ${videoIdMap[videoId].map(idx => idx+1).join(', ')})`);
    } else {
      // Clear any previous coloring if not duplicate
      sheet.getRange(i + 1, col.url + 1).setBackground(null);
    }

    // 5. Only call YouTube API if we have a valid ID
    if (!videoId) {
      notes.push("❌ Invalid or missing YouTube ID");
      sheet.getRange(i + 1, col.notes + 1).setValue(notes.join('; '));
      continue;
    }

    try {
      const yt = YouTube.Videos.list("snippet,contentDetails", {id: videoId}).items[0];
      if (!yt) {
        notes.push("❌ Video not found via API");
        sheet.getRange(i + 1, col.notes + 1).setValue(notes.join('; '));
        continue;
      }

      // === Data from YouTube ===
      const ytTitle = yt.snippet.title;
      const ytChannel = yt.snippet.channelTitle;
      const ytDate = yt.snippet.publishedAt ? yt.snippet.publishedAt.split("T")[0] : '';
      const ytDuration = yt.contentDetails.duration;

      // USER column (YouTube channel/uploader)
      if (col.user >= 0) {
        if (!row[col.user] || row[col.user] !== ytChannel) {
          if (row[col.user] && row[col.user] !== ytChannel) {
            sheet.getRange(i + 1, col.user + 1).setBackground('orange');
            notes.push(`⚠️ User mismatch: was "${row[col.user]}", API "${ytChannel}"`);
          }
          sheet.getRange(i + 1, col.user + 1).setValue(ytChannel);
        } else {
          sheet.getRange(i + 1, col.user + 1).setBackground(null);
        }
      }

      // TITLE
      if (col.title >= 0) {
        if (!row[col.title] || row[col.title] !== ytTitle) {
          if (row[col.title] && row[col.title] !== ytTitle) {
            sheet.getRange(i + 1, col.title + 1).setBackground('orange');
            notes.push(`⚠️ Title mismatch: was "${row[col.title]}", API "${ytTitle}"`);
          }
          sheet.getRange(i + 1, col.title + 1).setValue(ytTitle);
        } else {
          sheet.getRange(i + 1, col.title + 1).setBackground(null);
        }
      }

      // DATE
      if (col.date >= 0) {
        const sheetDate = row[col.date];
        let formattedSheetDate;
        if (sheetDate instanceof Date) {
          formattedSheetDate = Utilities.formatDate(sheetDate, Session.getScriptTimeZone(), "yyyy-MM-dd");
        } else if (typeof sheetDate === "string" && sheetDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
          // already in ISO
          formattedSheetDate = sheetDate;
        } else if (typeof sheetDate === "string" && sheetDate.length) {
          try {
            var tryDate = new Date(sheetDate);
            if (!isNaN(tryDate)) {
              formattedSheetDate = Utilities.formatDate(tryDate, Session.getScriptTimeZone(), "yyyy-MM-dd");
            }
          } catch (e) {
            // ignore invalid dates
          }
        }
        const ytDateString = yt.snippet.publishedAt ? yt.snippet.publishedAt.split("T")[0] : '';
        if (!formattedSheetDate || formattedSheetDate !== ytDateString) {
          if (formattedSheetDate && formattedSheetDate !== ytDateString) {
            sheet.getRange(i + 1, col.date + 1).setBackground('orange');
            notes.push(`⚠️ Date mismatch: was "${formattedSheetDate}", API "${ytDateString}"`);
          }
          sheet.getRange(i + 1, col.date + 1).setValue(ytDateString);
        } else {
          sheet.getRange(i + 1, col.date + 1).setBackground(null);
        }
      }

      // DURATION (robust normalized comparison, handles numbers, blanks, all types)
      if (col.duration >= 0) {
        const normDuration = normalizeDuration(ytDuration);
        const ytSeconds = durationToSeconds(ytDuration);

        let sheetDuration = row[col.duration];
        let sheetSeconds;

        if (
          sheetDuration === undefined ||
          sheetDuration === null ||
          (typeof sheetDuration !== 'string' && typeof sheetDuration !== 'number')
        ) {
          sheetDuration = '';
          sheetSeconds = 0;
        } else if (typeof sheetDuration === 'number') {
          sheetSeconds = sheetDuration;
          let h = Math.floor(sheetDuration / 3600);
          let m = Math.floor((sheetDuration % 3600) / 60);
          let s = sheetDuration % 60;
          let isoString = 'PT' + (h > 0 ? h + 'H' : '') + (m > 0 ? m + 'M' : '') + (s > 0 ? s + 'S' : '');
          sheetDuration = normalizeDuration(isoString);
        } else {
          sheetSeconds = durationToSeconds(sheetDuration);
        }

        if (!sheetDuration || sheetSeconds !== ytSeconds) {
          if (sheetDuration && sheetSeconds !== ytSeconds) {
            sheet.getRange(i + 1, col.duration + 1).setBackground('orange');
            notes.push(`⚠️ Duration mismatch: was "${row[col.duration]}", API "${normDuration}"`);
            mismatchCount++;
          }
          sheet.getRange(i + 1, col.duration + 1).setValue(normDuration);
          updatedCount++;
        } else {
          sheet.getRange(i + 1, col.duration + 1).setBackground(null); // Always clear if correct!
        }
      }




      
    } catch (err) {
      notes.push("❌ API error");
      Logger.log(err);
      errorCount++;
    }

    // Write any warnings or info in Researcher Notes
    if (col.notes >= 0) {
      sheet.getRange(i + 1, col.notes + 1).setValue(notes.join('; '));
    }
  }

  Logger.log(`YouTube Metadata Sync: Updated ${updatedCount} rows, found ${mismatchCount} mismatches, and ${errorCount} errors.`);
}
function doPost(e) {
  syncYouTubeMetadata();
  return ContentService.createTextOutput('OK');
}

function doGet(e) {
  return ContentService.createTextOutput('Web App is running! Use POST to trigger sync.');
}