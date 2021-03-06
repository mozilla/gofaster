$(function() {
  var router = Router({
    '/builds': {
      '/:buildid': {
        state: {},
        on: function(buildid) {
          $('#build-dialog').dialog({
            autoOpen: false,
            close: function(event, ui) { window.location.hash = '/builds/' + buildid; },
            width: 540,
            height: 560,
            modal: true
          });

          $.getJSON('api/builds/' + buildid + '/', function(data) {
            var events = data['events'];
            var summary = data['summary'];

            var min_time = events.map(function(x) {
              return x.submitted_at;
            }).reduce(function(x,y) {
              return Math.min(x,y);
            });

            var max_time = events.map(function(x) {
              return x.finish_time;
            }).reduce(function(x,y) {
              return Math.max(x,y);
            });

            var submitted_date = new Date(summary['submitted_at']*1000);

            $('#header').html(ich.buildchart_header({ build_id: summary['uid'],
                                                         revision: summary['revision'],
                                                         date: submitted_date.toUTCString(),
                                                         totaltime: ((summary['time_taken_overall'])/60.0/60.0).toFixed(3) }));

            $('#buildchart').width(((max_time-min_time)/60.0)*5); // 5 pixels/minute (+ some extra space for text)
            $('#buildchart').height(events.length*25); // 25 pixels per event

            function get_relative_time(t) {
              return (t-min_time)/60.0/60.0;
            }

            var i=events.length;
            var event_series = [];
            var submitted_series = [];
            events.forEach(function(event) {
              // get job description
              var jobtype = event.jobtype;
              if (event.jobtype !== "talos") {
                jobtype = [ event.buildtype, event.jobtype ].join(" ");
              }
              if (event.suitename) {
                jobtype += " (" + event.suitename + ")";
              }

              function toMinuteString(seconds) {
                return (seconds/60.0).toFixed(3) + " min";
              }

              var desc = event.description + ' ' + toMinuteString(event.finish_time - event.start_time) + " (wait: " + toMinuteString(event.start_time - event.submitted_at) + ")";
              var build_job_id = event.build_job_id ? event.build_job_id : null;
              event_series[event_series.length] = [get_relative_time(event.start_time), i, get_relative_time(event.finish_time), desc, build_job_id];
              submitted_series[submitted_series.length] = [get_relative_time(event.submitted_at), i, get_relative_time(event.start_time), null];
              i--;
            });
            var options = { series: { gantt: { active: true, show: true, barheight: 0.2 } }
		            ,xaxis:  { min: 0, max: get_relative_time(max_time)+1, axisLabel: 'Time (hours)' }
		            ,yaxis:  { min: 0, max: event_series.length + 0.5, ticks: 0 }
		            ,grid:   { hoverable: true, clickable: true}
   		          };
            $.plot($("#buildchart"), [ { label: "Events", data: event_series }, { label: "Wait times", data: submitted_series } ], options);

            $("#buildchart").bind("plotclick", function(event, pos, obj) {
              var build_job_id = obj.datapoint[4];
              if (!build_job_id) {
                return;
              }
              window.location.hash = '/' + [ 'builds', buildid, 'buildjobs', build_job_id ].join('/');
            });
          });
        },

        '/buildjobs/([0-9]+)': {
          on: function(buildid, jobid) {
            $.getJSON('api/buildjobs/' + jobid + '/', function(data) {
              if (!data) {
                $('#build-dialog').dialog('option', 'title', 'No data');
                $('#piechart').hide();
                $('#full-log').hide();
                $('#description').html('<p>No data for this job. Sorry. :( Either it\'s too old or there\'s a bug in our system.</p>');
                $('#build-dialog').dialog('open');
                return;
              }

              $('#build-dialog').dialog('option', 'title', data['description'] + ' on ' + data['machine']);
              $('#piechart').show();
              $('#full-log').show();
              $('#description').html('<p><br/></p>');
              $('#full-log').html('<p>Total time: ' + data['total'] + ' minutes. <a href=\"' + data['logurl'] + '\" target=\"_blank\">Full Log</p>');
              $('#build-dialog').dialog('open');

              var builddata = Object.keys(data['steps']).map(function(stepname) {
                return { label: stepname, data: data['steps'][stepname] };
              });
              $.plot($('#piechart'), builddata,
	             {
	               series: {
	                 pie: {
	                   show: true,
                           combine: {
                             color: '#999',
                             threshold: 0.025
                           }
	                 }
	               },
                       grid: {
                         hoverable: true,
                         clickable: true
                       }
	             });
              $('#piechart').bind('plothover', function(event, pos, obj) {
                if (obj) {
                  $('#description').html('<p style="font-weight: bold; align: center;">'+obj.series.label+' ('+obj.series.data[0][1]+' minutes)</span>');
                } else {
                  $('#description').html('<p><br/></p>');
                }
              });
            });
          }
        }
      }
    }
  }).use({recurse: 'forward'}).init();
});
