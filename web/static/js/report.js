function createReportkRow(heading, content) {
  return '<tr>' +
         '<th>' + heading + '</th>' +
         '<td>' + content + '</td>' +
         '</tr>';
}

function reportSetup(apiLoc, taskId) {
  // Get list of tasks and populate the table
  tasks_data = $.get("http://" + apiLoc + "/api/v1/tasks/report/" + taskId, function(data, status){
    $.each(data.Report, function(index, item) {
      $("tbody").append(createReportkRow(index, item));
    });

  });
}