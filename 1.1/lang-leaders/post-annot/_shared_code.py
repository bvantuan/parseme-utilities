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


def consistency_and_adjudication_shared_javascript():
    r'''Get shared javascript code for utility HTML pages
    (we do not use a separate javascript file because we want things to be as SIMPLE as possible).
    '''

    return '''
        <!--- BEGIN SHARED --->
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
        function resetDecision(decisionButtonOrNull) {
            var decisionButton = decisionButtonOrNull || $("#active-decide-button");
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

        function readJsonFile(filePath) {
            var reader = new FileReader();
            reader.onload = function() {
              var havePending = window.havePendingParsemeNotes;
              var data = JSON.parse(reader.result);
              var decisions = data.DECISIONS;
              if (!_.isEqual(data.META.filename_mapping, window.parsemeFilenameMapping)) {
                  alert('WARNING:\\n\\nParsemeNotes file has this file mapping:\\n  ' + JSON.stringify(data.META.filename_mapping) + '\\nBut this HTML file was created with this mapping:\\n  ' + JSON.stringify(window.parsemeFilenameMapping) + '\\n\\nDo not proceed if these do not match!');
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
        <!--- END SHARED --->\n
    '''
