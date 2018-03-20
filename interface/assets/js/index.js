var refresh_rate = 2000;
var tabs_instance;
var job_modal_instance;
var confirm_delete_modal_instance;
var job_fab_instance;
var node_fab_instance;
var dropdown_instance;
var login_server = 'login.php';
var logout_server = 'logout.php';
var authentication_server = 'authenticated.php';
var info_server = 'global_list.php';
var cmd_server = 'execute_cmd.php';

$(document).ready(function () {
    $.ajax(authentication_server).done(function (data) {
        console.log('Login status: ' + data);
        try {
            data = JSON.parse(data);
        } catch (err) {
            $('.login-status').text("Unknown response from the server").addClass('red').addClass('scale-in');
        }
        if (data.authenticated == 1) {
            login_success();
        } else {
            $('.login-overlay').removeClass('active');
            if ('error' in data) $('.login-status').text("Failed to connect to credientials server").addClass('red').addClass('scale-in');
            $('.login-overlay').removeClass('active');
        }
    }).fail(function () {
        $('.login-status').text("Failed to connect to credientials server").addClass('red').addClass('scale-in');
        $('.login-overlay').removeClass('active');
    });
});


$('#username, #password').on("input", function () {
    let empty = false;
    $('#username, #password').each(function () {
        if (this.value.length == 0) empty = true;
    });
    if (!empty) {
        $('#submit').removeClass('disabled');
    } else {
        $('#submit').addClass('disabled');
    }
});


$('#submit').click(function (event) {
    event.preventDefault();

    $('.login-form button').addClass('disabled');
    $('.login-form input').attr('disabled', '');
    $('.login-overlay').addClass('active');

    $.post({
        url: login_server,
        data: {
            'USER': $('#username').val(),
            'PASS': $('#password').val()
        }
    }).done(function (data) {
        console.log('Response: ' + data);
        let response = JSON.parse(data);
        let error = null;
        if (typeof response.error !== 'undefined') {
            error = response.error;
        } else if (typeof response.authenticated !== 'undefined' && response.authenticated == 0) {
            error = response.error;
        } else if (typeof response.authenticated !== 'undefined' && response.authenticated == 1) {

            login_success();

        }
        if (error != null) $('.login-status').text(error).addClass('red').removeClass('hide').addClass('scale-in');
    }).fail(function (data) {
        console.log(data);
        $('.login-status').text("Failed to connect to credientials server").addClass('red').addClass('scale-in');
    }).always(function () {
        $('.login-form button').removeClass('disabled');
        $('.login-form input').removeAttr('disabled');
        $('.login-overlay').removeClass('active');
    });

    return false;
})


$('#new-job-filename').on('input', function () {
    if ($('#new-job-filename').val().length == 0) {
        $('#new-job-submit').addClass('disabled');
    } else {
        $('#new-job-submit').removeClass('disabled');
    }
});


function show_login() {
    $('.login-form button').removeClass('disabled');
    $('.login-form input').removeAttr('disabled');
    $('.login-overlay').removeClass('active');
    $('.login-wrapper').removeClass('fade-out');
}

function login_success() {
    $('.login-form button').removeClass('disabled');
    $('.login-form input').removeAttr('disabled');
    $('.login-overlay').removeClass('active');
    $('.login-wrapper').addClass('fade-out');
    $("#password").val('');

    var tabs = document.querySelector('.tabs');
    tabs_instance = M.Tabs.init(tabs);

    var job_modal = document.getElementById('new-job-modal');
    job_modal_instance = M.Modal.init(job_modal, {
        dismissible: false,
        onOpenEnd: function () {
            $('#new-job-filename').focus();
        }
    });

    var confirm_delete_modal = document.getElementById('delete-confirm-modal');
    confirm_delete_modal_instance = M.Modal.init(confirm_delete_modal, {
        dismissible: false
    });

    var job_fab = document.getElementById('job-fab');
    job_fab_instance = M.FloatingActionButton.init(job_fab);

    var node_fab = document.getElementById('node-fab');
    node_fab_instance = M.FloatingActionButton.init(node_fab);

    var dropdown = document.querySelector('.dropdown-trigger');
    dropdown_instance = M.Dropdown.init(dropdown);

    document.querySelectorAll('.tooltipped').forEach(function (item) {
        M.Tooltip.init(item);
    });

    $('.landing').scope().init(); // Start the app
}

var app = angular.module("landing_app", []);

app.directive('ngEnter', function () {
    return function (scope, element, attrs) {
        element.bind("keydown keypress", function (event) {
            if (event.which === 13) {
                scope.$apply(function () {
                    scope.$eval(attrs.ngEnter);
                });

                event.preventDefault();
            }
        });
    };
});

app.controller("landing_controller", function ($scope, $window) {

    $scope.init = function () {
        $scope.interval = setInterval($scope.update_json, refresh_rate);
        $scope.update_json();
    };

    $scope.status_codes = {
        'Imported': 0,
        'Ingesting': 1,
        'Transcoding': 2,
        'Transcoded': 3,
        'Exporting': 4,
        'Complete': 5,
        'Failed': 13
    };

    $scope.node_type = {
        'Ingest': 0,
        'Transcode': 1,
        'Export': 2
    }

    $scope.fecthing = false;
    $scope.refresh = true;
    $scope.selecting = false;
    $scope.data = {};
    $scope.completion = {};
    $scope.state = {};
    $scope.action = '';
    $scope.selections = {};
    $scope.old_refresh;
    $scope.policy_update = false;
    $scope.interval = null;
    $scope.new_policies = {};
    $scope.upload_policies = false;

    $scope.submit_new_job = function (close) {
        if (close == true) $window.job_modal_instance.close();

        if ($('#new-job-filename').val().length == 0) {
            M.toast({
                html: 'Filename was empty! No job was added.'
            })
        } else {
            let filename = $('#new-job-filename').val();

            $.post(cmd_server, {
                CMD: 'new_job',
                source_name: filename

            }, 'json').fail(function () {
                M.toast({
                    html: 'Could not submit the request to the server. Check your internet connection.'
                })

            }).done(function (data) {
                let json = JSON.parse(data);
                if (json['authenticated'] == 0) {
                    M.toast({
                        html: 'Could not create the job! Your login expired.'
                    });
                    show_login();
                } else if (json['success'] == 1) {
                    M.toast({
                        html: 'Job was created!'
                    });
                } else if (json['success'] == 0) {
                    M.toast({
                        html: 'Could not create the job. ' + json['error']
                    });
                } else {
                    M.toast({
                        html: 'Unknown response from server'
                    });
                }
                console.log('Response for command execution:');
                console.log(json);
            });

        }
    }


    $scope.update_json = function () {
        if (!$scope.fetching && $scope.refresh) {
            $scope.fetching = true;

            $.get(info_server).done(function (result) {
                let processed_response = $scope.process(JSON.parse(result));
                if (!(JSON.stringify(processed_response) === JSON.stringify($scope.data))) {
                    $scope.data = processed_response;

                    for (let key in $scope.data.jobs) {
                        let job = $scope.data.jobs[key];

                        if (job.status == $scope.status_codes.Imported) {
                            $scope.completion[job.jobID] = 0;
                            $scope.state[job.jobID] = 'grey';
                        } else if (job.status == $scope.status_codes.Ingesting) {
                            $scope.completion[job.jobID] = 5;
                            $scope.state[job.jobID] = 'orange';
                        } else if (job.status == $scope.status_codes.Transcoding) {
                            let count = 0;
                            for (let t_key in job.transcodeJob) {
                                if (job.transcodeJob[t_key].status == 2) count++;
                            }
                            $scope.completion[job.jobID] = ((count / Object.keys(job.transcodeJob).length) * 80 + 10);
                            $scope.state[job.jobID] = 'orange';
                        } else if (job.status == $scope.status_codes.Transcoded) {
                            $scope.completion[job.jobID] = 90;
                            $scope.state[job.jobID] = 'orange';
                        } else if (job.status == $scope.status_codes.Exporting) {
                            $scope.completion[job.jobID] = 95;
                            $scope.state[job.jobID] = 'orange';
                        } else if (job.status == $scope.status_codes['Complete']) {
                            $scope.completion[job.jobID] = 100;
                            $scope.state[job.jobID] = 'green';
                        } else if (job.status == $scope.status_codes['Failed']) {
                            $scope.completion[job.jobID] = 100;
                            $scope.state[job.jobID] = 'red';
                        }

                    };

                    $scope.$apply();
                }
            }).always(function () {
                $scope.fetching = false;
            });
        }
    };


    $scope.start_action = function () {
        $('.landing').addClass('action');
        $('.tab').addClass('disabled');
        $('.fixed-action-btn').addClass('scale-out');
        $scope.selections = {};
        $scope.selecting = true;
        $scope.refresh = false;
        $scope.action = '';
    }

    $scope.stop_action = function () {
        $('.landing').removeClass('action ja-delete na-authorise na-deauthorise na-terminate')
        $('.tab').removeClass('disabled');
        $('.fixed-action-btn').removeClass('scale-out');
        $scope.selecting = false;
        $scope.refresh = true;
        $scope.selections = {};
    }

    $scope.job_delete = function () {
        $scope.start_action();
        $scope.action = 'delete_job';
        $('.landing').addClass('ja-delete');
    }


    $scope.node_authorise = function () {
        $scope.start_action();
        $scope.action = 'authorise_node';
        $('.landing').addClass('na-authorise');
    }


    $scope.node_deauthorise = function () {
        $scope.start_action();
        $scope.action = 'deauthorise_node';
        $('.landing').addClass('na-deauthorise');
    }

    $scope.node_terminate = function () {
        $scope.start_action();
        $scope.action = 'terminate_node';
        $('.landing').addClass('na-terminate');
    }

    $('#action-dropdown a').click(function (event) {
        let action = event.target.getAttribute('action');
        if (action == 'select-none') {
            $scope.selections = {};

        } else if (action.includes('all')) {
            if (['delete_job'].includes($scope.action)) {
                for (let job in $scope.data.jobs) {
                    $scope.selections[$scope.data.jobs[job].jobID] = true;
                }
            } else if (['authorise_node', 'deauthorise_node', 'terminate_node'].includes($scope.action)) {
                for (let node in $scope.data.nodes) {
                    $scope.selections[$scope.data.nodes[node].nodeID] = true;
                }
            }

        }

        if (action == 'delete-selected-jobs') {
            $scope.id_list = $scope.return_keys($scope.selections);
            $('#confirm-delete-button').html('DELETE');
            $window.confirm_delete_modal_instance.open()
            $scope.stop_action();

        } else if (action == 'delete-all-jobs') {
            $scope.id_list = $scope.return_keys($scope.selections);
            $('#confirm-delete-button').html('DELETE ALL');
            $window.confirm_delete_modal_instance.open();
            $scope.stop_action();

        } else if (!action.includes('select-')) {
            $scope.id_list = $scope.return_keys($scope.selections);
            $scope.confirm_action($scope.action);
            $scope.stop_action();
        }

        setTimeout(function () {
            $scope.$apply()
        }, 1);
    });

    $scope.action_toasts = {
        'delete_job': {
            0: 'Failed to remove jobs',
            1: 'Jobs removed',
            2: 'Some jobs were\'nt removed'
        },
        'authorise_node': {
            0: 'Failed to authorise nodes',
            1: 'Nodes authorised',
            2: 'Some nodes were\'nt authorised'
        },
        'deauthorise_node': {
            0: 'Failed to deauthorise nodes',
            1: 'Nodes deauthorised',
            2: 'Some nodes were\'nt deauthorised'
        },
        'terminate_node': {
            0: 'Failed to terminate nodes',
            1: 'Nodes terminated',
            2: 'Some nodes were\'nt terminated'
        }
    }

    $scope.get_action_toast = function (action, success) {
        if (!(action in $scope.action_toasts)) {
            if (success == 1) return 'Command executed';
            return 'Unknown action';
        } else {
            if (!(success in $scope.action_toasts[action])) {
                return 'Unrecognised success code: ' + success + ' for action ' + action;
            }
        }
        return $scope.action_toasts[action][success];
    }

    $scope.confirm_action = function () {
        let action = $scope.action;
        $.post(cmd_server, {
            CMD: $scope.action,
            'ids': JSON.stringify($scope.id_list)
        }).done(function (data) {
            console.log('Command server response:' + data);
            let response = JSON.parse(data);
            M.toast({
                html: $scope.get_action_toast(action, response.success)
            });
        }).fail(function () {
            M.toast({
                html: '<a class="red">Could not connect to command execution server</a>'
            });
        });
    }

    $scope.$watch('refresh', function (new_value, old_value) {
        if (new_value == true) {
            $scope.interval = setInterval($scope.update_json, refresh_rate);

        } else {
            clearInterval($scope.interval);
        }
    });

    $scope.pretty_policies = {
        'ingestEnabled': 'Ingest authorised',
        'transcodeEnabled': 'Transcode authorised',
        'exportEnabled': 'Export authorised',
        'terminateAll': 'Terminate all nodes',
        'verifyDuringIngest': 'Enable ingest integrity verification',
        'nodeTimeout': 'Database node timeout [seconds]',
        'failureTolerance': 'Maximum failure tolerancy'
    }

    $scope.$watch('policy_update', function (new_value, old_value) {

        if (new_value == true) {
            $('.tab').addClass('disabled');
            $('.refresh').addClass('hide');
            $scope.new_policies = {};
            for (let key in $scope.data.policies) {
                $scope.new_policies[$scope.data.policies[key].policy] = $scope.data.policies[key].value;
            }
            console.log($scope.new_policies);
            $scope.refresh = false;
            setTimeout(function () {
                $scope.$apply;
                $scope.upload_policies = true;
            }, 1);

        } else {
            $('.tab').removeClass('disabled');
            $('.refresh').removeClass('hide');
            $scope.refresh = true;
            $scope.upload_policies = false;
            $scope.new_policies = {};
        }
    });

    $scope.$watch('new_policies', function (new_value, old_value) {
        if ($scope.policy_update == true && $scope.upload_policies) {
            let obj = {};
            let data_types = {};

            for (let pol in $scope.data.policies) {
                data_types[$scope.data.policies[pol].policy] = $scope.data.policies[pol].value_type;
            }
            console.log(data_types);

            for (let key in new_value) {
                if (new_value[key] !== old_value[key]) {
                    if (data_types[key] == 'boolean') {
                        if (new_value[key] == true) {
                            obj[key] = 1;
                        } else {
                            obj[key] = 0;
                        }
                    } else {
                        obj[key] = new_value[key];
                    }
                }
            }

            $.post(cmd_server, {
                CMD: 'update_policy',
                policies: JSON.stringify(obj)
            }).done(function (data) {
                console.log('Command server response:' + data);
                let response = JSON.parse(data);
                M.toast({
                    html: 'Policy updated'
                });
            }).fail(function () {
                M.toast({
                    html: '<a class="red">Could not connect to command execution server</a>'
                });
            });
        }
    }, true);

    $scope.logout = function () {
        $scope.stop_action();
        $scope.policy_update = false;
        $scope.refresh = false;
        $('.login-form input').attr('disabled', '');
        $('.login-overlay').addClass('active');
        $('.login-wrapper').removeClass('fade-out');

        $.ajax(logout_server).always(function () {
            $('.login-form input').removeAttr('disabled');
            $('.login-overlay').removeClass('active');
        });

        $('input').trigger('input');
    }


    $scope.process = function (data) {
        let array = Object.assign({}, data);
        for (let key in array) {
            if (typeof array[key] == 'object') array[key] = $scope.process(array[key]);
            if (typeof array[key] == 'string' && !isNaN(array[key])) {
                array[key] = parseInt(array[key]);
            }
        }
        if ('value' in array && 'value_type' in array && array.value_type == 'boolean') {
            array.value = !!array.value;
        }
        return array;
    }

    $scope.get_key = function (object, value) {
        for (let key in object) {
            if (object[key] === value) {
                return key;
            }
        }
    };

    $scope.return_keys = function (obj) {
        let array = [];
        for (let key in obj) {
            if (isNaN(key)) {
                array.push(key);
            } else {
                array.push(parseInt(key));
            }
        }
        return array;
    }


    $scope.get_active_jobs = function () {
        let array = $scope.data.jobs;
        let count = 0;
        for (let key in array) {
            if (array[key].status < 5) count++;
        }

        return count;
    }

    $scope.get_nodes = function () {
        if (typeof $scope.data == 'object' && typeof $scope.data.nodes == 'object') {
            return Object.keys($scope.data.nodes).length;
        }
        return '?';
    }
    
    $scope.get_saturation = function() {
        
        let array = $scope.data.nodes;
        let count = 0;
        for (let key in array) {
            if (array[key].isActive == 1) count++;
        }
        if (typeof array != 'undefined') {
            if (Object.keys(array).length == 0) return 'No nodes';
            return parseInt( count / Object.keys(array).length * 100) + '%';
    }
    return 'No data...';
        
    }
    
    $scope.errors = function() {
        let jobs = $scope.data.jobs;
        if (typeof jobs != 'undefined') {
            for (let key in jobs) {
                if (jobs[key].status == 13) return true;
            }
        }
        
        return false;
    }

});




function isEmpty(obj) {

    // null and undefined are "empty"
    if (obj == null) return true;

    // Assume if it has a length property with a non-zero value
    // that that property is correct.
    if (obj.length > 0) return false;
    if (obj.length === 0) return true;

    // If it isn't an object at this point
    // it is empty, but it can't be anything *but* empty
    // Is it empty?  Depends on your application.
    if (typeof obj !== "object") return true;

    // Otherwise, does it have any properties of its own?
    // Note that this doesn't handle
    // toString and valueOf enumeration bugs in IE < 9
    for (var key in obj) {
        if (hasOwnProperty.call(obj, key)) return false;
    }

    return true;
}
