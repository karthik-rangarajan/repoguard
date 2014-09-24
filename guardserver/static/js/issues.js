jQuery(function(){
    var valid_tab = Object();
    valid_tab.current_page = 1;
    valid_tab.size = 10;
    var invalid_tab = Object();
    invalid_tab.current_page = 1;
    invalid_tab.size = 10;
    localStorage.setItem("valid_tab", JSON.stringify(valid_tab));
    localStorage.setItem("invalid_tab", JSON.stringify(invalid_tab));
    get_issues(false);
    get_issues(true);
});

function get_issues(false_positive) {
    var tab_state;
    if (false_positive) {
        tab_state = JSON.parse(localStorage.getItem("invalid_tab"));
    }
    else {
        tab_state = JSON.parse(localStorage.getItem("valid_tab"));
    }
    var start_time = localStorage.getItem("start_date");
    var end_time = localStorage.getItem("end_date");
    var params = Object();
    params.start_time = start_time;
    params.end_time = end_time;
    params.from = (tab_state.current_page - 1) * tab_state.size;
    params.to = tab_state.size;
    params.false_positive = false_positive;
    server = localStorage.getItem("server");
    $.getJSON(server + "/issues/", params=params, function(data){
        if (!false_positive) {
            add_issues_to_table(data.issues, "#issue-body-valid");
            localStorage.setItem("valid-issues", data.total);
        }
        else {
            add_issues_to_table(data.issues, "#issue-body-invalid");
            localStorage.setItem("invalid-issues", data.total);
        }

    })
}

function add_issues_to_table(data, dom_element) {
    $(dom_element).empty();
    $.each(data, function(){
        var source = this["_source"];
        var status_change = source["false_positive"] == "true" ? ["Valid", false]: ["Invalid", true];
        var table_row = '<tr data-repo="' + source["repo_name"] + '">' +
            "<td>" + source["repo_name"] + "</td>" +
            "<td>" + $("<div />").text(source["matching_line"]).html() + "</td>" +
            '<td id="' + source["commit_id"] + '"><a href="javascript:void(0)" title="Click to show file">' + source["filename"] + "</a></td>" +
            "<td>" + source["commit_description"] + "</td>" +
            "<td title='" + source["description"] + "'>" + source["check_id"] + "</td>" +
            "<td class='reviewer'>" + source["last_reviewer"] + "</td>" +
            '<td><button type="button" class="btn btn-primary" id="' + this["id"] + '" data-status="' + status_change[1] + '">' +
            'Mark As ' + status_change[0] + '</button>' +
            "</tr>";
        $(dom_element).prepend(table_row);
        $("#" + source["commit_id"]).click(function(){
            var commit_id = $(this).attr('id');
            var params = Object();
            params.repo = $(this).closest('tr').attr('data-repo');
            params.file_path = $(this).text();
            $.get(server + "/issue/get_contents/" + commit_id, params=params, function(data){
                $("#code-space").append($("<div />").text(data).html());
                $("#code-holder").modal('show');
            });
        });
        $("#" + this["id"]).click(function(){
            var index_id = $(this).attr('id');
            var data_status = $(this).attr('data-status');
            var table_row = $(this).closest('tr');
            var params = Object();
            params.status = (data_status === "true");
            params.current_user = localStorage.getItem("current_user");

            $.ajax({
                url: server + "/issue/status/" + index_id,
                type: 'PUT',
                data: params,
                success: function(data) {
                    $("#" + index_id).attr("data-status", !params.status);
                    if (!params.status) {
                        $("#" + index_id).text("Mark as Invalid").closest("tr").find(".reviewer").text(localStorage.getItem("current_user"));
                        $("#issue-body-valid").append($(table_row).clone(true, true));
                    }
                    else {
                        $("#" + index_id).text("Mark as Valid").closest("tr").find(".reviewer").text(localStorage.getItem("current_user"));
                        $("#issue-body-invalid").append($(table_row).clone(true, true));
                    }
                    $(table_row).remove();
                }
            })
        })
    });
}