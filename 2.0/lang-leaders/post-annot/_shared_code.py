def html_header():
    r'''Get HTML header including JS script URLs.'''
    return '''
        <html>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.5/lodash.min.js"></script>
    '''


def global_box_and_warning_modal():
    r'''Get HTML code for the global-box and the warning modal.'''
    return '''
        <div class="global-box">
            Notes added: <span id="global-counter">0</span>

            <div><a class="global-link" href="javascript:writeJsonFile()">Generate JSON</a></div>

            <label for="file-upload" class="global-link global-file-input">Load JSON file</label>
            <input style="display:none" id="file-upload" type="file" onchange="javascript: readJsonFile(this, this.files[0])"/>
        </div>

        <style>
        #mapping-warning-modal-title {
            font-weight: bold;
            color: red;
        }
        #mapping-warning-modal-body {
            font-weight: bold;
        }
        #mapping-warning-html, #mapping-warning-json {
            font-size: 11px;
            margin-bottom: 20px;
            font-weight: normal;
        }
        </style>

        <!-- "Warning" modal -->
        <div id="mapping-warning-modal" class="modal fade" role="dialog">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <!-- <button type="button" class="close" data-dismiss="modal">&times;</button> -->
                <h4 id="mapping-warning-modal-title" class="modal-title">Warning</h4>
              </div>
              <div id="mapping-warning-modal-body" class="modal-body">
                  <p>The HTML file was created with this mapping:</p>
                  <p id="mapping-warning-html"></p>
                  <p>But the ParsemeNotes JSON file contains this mapping:</p>
                  <p id="mapping-warning-json"></p>
                  <p>Do not proceed if these mappings do not match!</p>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
              </div>
            </div>

          </div>
        </div>
    '''


def consistency_and_adjudication_shared_javascript():
    r'''Get shared javascript code for utility HTML pages
    (we do not use a separate javascript file because we want things to be as SIMPLE as possible).
    '''

    return '''
        <!--- ============ --->
        <!--- BEGIN SHARED --->
        window.parsemeData = {};
        window.havePendingParsemeNotes = false;


        function escapeRegExp(str) {
            return str.replace(''' + r"/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g" + ''', "\\$&");
        }
        /** Return whether the space-separated tokens in innerText appears inside fullText */
        function areTokensInside(fullText, innerText) {
            var regex = escapeRegExp(innerText).replace(/ +/g, ".*");
            return new RegExp(regex, "g").test(fullText);
        }

        /** Remove note from window.parsemeData and update GUI */
        function resetDecision(decisionButton) {
            window.havePendingParsemeNotes = true;
            var entryID = calculateEntryID(decisionButton);
            delete window.parsemeData[entryID];
            unmarkDecisionButton(decisionButton);
            updateCounter();
            killDropdown();
        }


        /*
         * File format:
         * {
         *   "META": {"parseme_version": "x.y", ...},
         *   "DECISIONS": {...}
         * }
         */
        function writeJsonFile() {
            var parsemeData = {
                "META": {
                    "parseme_version": "1.1",
                    "parseme_json_version": "2.0",
                    "filename_mapping": window.parsemeFilenameMapping,
                },
                "DECISIONS": window.parsemeData
            }
            var json = JSON.stringify(parsemeData, null, 2);
            var blob = new Blob([json], {type: "application/json"});
            var url  = URL.createObjectURL(blob);
            saveAs(url, "ParsemeNotes.json");
            window.havePendingParsemeNotes = false;  // assume they have downloaded it...
        }
        function saveAs(uri, filename) {
            var link = document.createElement('a');
            if (typeof link.download === 'string') {
                document.body.appendChild(link); // Firefox requires the link to be in the body
                link.download = filename;
                link.href = uri;
                link.click();
                document.body.removeChild(link); // remove the link when done
            } else {
                location.replace(uri);
            }
        }

        function readJsonFile(inputForm, filePath) {
            inputForm.value = null;  /* allow same file file reload to trigger onchange */
            var reader = new FileReader();
            reader.onload = function() {
              var havePending = window.havePendingParsemeNotes;
              var data = JSON.parse(reader.result);
              var decisions = data.DECISIONS;
              if (!_.isEqual(data.META.filename_mapping, window.parsemeFilenameMapping)) {
                  $('#mapping-warning-html').text(JSON.stringify(data.META.filename_mapping, null, 1));
                  $('#mapping-warning-json').text(JSON.stringify(window.parsemeFilenameMapping, null, 1));
                  $('#mapping-warning-modal').modal();
              }
              $(".mweoccur-decide-button").each(function() {
                  var entryID = calculateEntryID(this);
                  if (decisions[entryID]) {
                      var annotEntry = decisions[entryID];
                      addNote($(this), annotEntry);
                  }
              });
              window.havePendingParsemeNotes = havePending;
            };
            reader.readAsText(filePath);
        }


        function updateCounter() {
            $("#global-counter").text(Object.keys(window.parsemeData).length);
        }

        <!--- END SHARED --->
        <!--- ============ --->\n
    '''
