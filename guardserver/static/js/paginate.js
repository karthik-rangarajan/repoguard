jQuery(function(){

    var previous_button_valid = $("#valid-previous");
    var previous_button_invalid =  $("#invalid-previous");
    var next_button_valid = $("#valid-next");
    var next_button_invalid = $("#invalid-next");

    previous_button_valid.addClass("disabled");
    previous_button_invalid.addClass("disabled");

    var valid_tab_state = JSON.parse(localStorage.getItem("valid_tab"));
    var invalid_tab_state = JSON.parse(localStorage.getItem("invalid_tab"));

    if (valid_tab_state.size > localStorage.getItem("valid-issues")) {
        next_button_valid.addClass("disabled");
    }

    if (invalid_tab_state.size > localStorage.getItem("invalid-issues")) {
        next_button_invalid.addClass("disabled");
    }

    previous_button_valid.click(function(){
        change_page(true, false, this, "#valid-next");
    });

    next_button_valid.click(function(){
        change_page(true, true, this, "#valid-previous");
    });

    previous_button_invalid.click(function(){
        change_page(false, false, this, "#invalid-next");
    });

    next_button_invalid.click(function(){
        change_page(false, true, this, "#invalid-previous");
    });

});

function change_page(valid_tab, next_page, this_element, dom_element) {
    var tab_state, key, issues_size;
    if (valid_tab) {
        tab_state = JSON.parse(localStorage.getItem("valid_tab"));
        key = "valid_tab";
        issues_size = localStorage.getItem("valid-issues");
    }
    else {
        tab_state = JSON.parse(localStorage.getItem("invalid_tab"));
        key = "invalid_tab";
        issues_size = localStorage.getItem("valid-issues");
    }
    if (next_page) {
        tab_state.current_page += 1;
        if (tab_state.current_page * tab_state.size > issues_size) {
            $(this_element).addClass("disabled");
        }
    }
    else {
        if (tab_state.current_page != 1) {
            tab_state.current_page -= 1;
            if (tab_state.current_page == 1) {
                $(this_element).addClass("disabled");
            }
        }
    }

    if ($(dom_element).hasClass("disabled")) {
        $(dom_element).removeClass("disabled");
    }
    localStorage.setItem(key, JSON.stringify(tab_state));
    get_issues(7, !valid_tab);
}