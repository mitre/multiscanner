function createTaskRow(row) {
  return '<tr class="task-row" data-href="/report/' + row.task_id + '">' +
         '<td>' + row.task_id + '</td>' +
         '<td>' + row.report_id + '</td>' +
         '<td>' + row.task_status + '</td>' +
         '<td class="text-center delete">' +
         '<button type="button" class="btn btn-danger btn-xs" data-toggle="tooltip" data-placement="bottom" title="" data-original-title="Delete this task?"><span class="glyphicon glyphicon-remove"></span></button>' +
         '</td></tr>';
}

function tasksSetup(apiLoc) {
  // Get list of tasks and populate the table
  tasks_data = $.get("http://" + apiLoc + "/api/v1/tasks/list/", function(data, status){
    // Add rows to the table
    $.each(data.Tasks, function(index, item) {
      console.log(index + '___'  + item)
      $("tbody").append(createTaskRow(item));
    });

    // Make table rows clickable
    $("td").click(function() {
      // But not cells with a Delete button
      if ($(this).hasClass('delete')) {
        return;
      }
      window.document.location = $(this).parent().data("href");
    });

    // Add tooltip to Delete buttons
    $(function () {
      $('[data-toggle="tooltip"]').tooltip();
    })
  });
}