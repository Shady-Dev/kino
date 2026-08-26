(function($) {
	$(document).ready( function() {
		
		var languageCode = nxt.TwoLetterLanguageCode;
		
		$( ".showlist" ).each(function( index ) {
			var serverurl = $(this).attr("data-api");
			if (!serverurl) {
				serverurl = nexxo_showlist.apiurl;
			}
			var baseurl = $(this).attr("data-imagebase");
			if (!baseurl) {
				baseurl = nexxo_showlist.baseurl;
			}
			var moviepage = nexxo_showlist.moviepage;
			var _locationid = $(this).attr("data-location");
			var _movieid = $(this).attr("data-movieid");
			var days = parseInt($(this).attr("data-days"));
			var showrooms = $(this).attr("data-showrooms") == "1";
			var showprices = $(this).attr("data-showprices") == "1";
			var showages = $(this).attr("data-showages") == '1';
			var showdescription = $(this).attr("data-showdescription") == '1';
			var showduration = $(this).attr("data-showduration") == '1';
			var showsite = $(this).attr("data-showsite") == '1';
			var showtimes = $(this).attr("data-showtimes") == '1';
			var showposter = $(this).attr("data-showposter") == '1';
			var showbanner = $(this).attr("data-showbanner") == '1';
			var linkimage = $(this).attr("data-linkimage") == '1';
			var onlytoday = $(this).attr("data-onlytoday") == '1';
			var showbackground = $(this).attr("data-showbackground") == '1';
			var showdates = $(this).attr("data-showdates") == '1';
			var onlytime = $(this).attr("data-onlytime") == '1';
			var linkmode = parseInt($(this).attr("data-linkmode"));
			var _showtype = parseInt($(this).attr("data-showtype"));
			var maxshows = parseInt($(this).attr("data-maxshows"));
			var room = parseInt($(this).attr("data-room"));
			var contenttypeid = parseInt($(this).attr("data-contenttypeid"));
			var _languagecode = $(this).attr("data-language");
			var _layout = $(this).attr("data-layout");
			var _upcoming = $(this).attr("data-upcoming") == '1';
			var target = $(this);
			if (serverurl) {
				
				$.ajax({
					type: "GET",
					dataType: 'json',
					data: {
						locationid: _locationid, 
						movieid: _movieid, 
						action: 'exportdailyshows', 
						upcoming: _upcoming, 
						showtype:_showtype, 
						roomid: room, 
						contenttypeid: contenttypeid,
						lang: languageCode,
						languagecode: _languagecode,
						days: days
					},
					url: serverurl ,
					success: function(msg) {
						drawShowList(target,msg, baseurl, moviepage, linkmode, linkimage, maxshows, showposter, showbanner, showbackground, showdescription, showduration, showsite, showages, showtimes,showrooms,showprices,showdates,onlytime,baseurl,_upcoming,_locationid,onlytoday,_layout);
						if (nexxo_showlist.targetshow) {
							jQuery(".aika[data-showid="+nexxo_showlist.targetshow+"]").first().click();
						}
					}
				});
			}
		});
		
		function drawShowList(target, msg, imgbase, moviepage, linkmode, linkimage, maxshows, showposter, showbanner, showbackground, showdescription, showduration, showsite, showages, showtimes,showrooms,showprices,showdates,onlytime,baseurl,upcoming,_locationid,onlytoday,_layout) {
			if (!msg) return;
			if (!baseurl) {
				baseurl = "/";
			}
			var outer = $("<div class='showlist_outer'></div>");
			
			var map = $('.showlist');
			if (target) {
				map = target;
			}
			map.show();
			
			var fullw = map.attr("data-fullwidth");
			if (fullw == '1') {
				outer.addClass("fullwidth");
			}
			
			if (linkmode > 0) {
				map.addClass("surroundlinks");
			}
			
			var needsEmpty = false;
			var children = map.children();
			
			if (children == null) {
				needsEmpty = true;
			} else {
				if (children.length == 0){
					needsEmpty = true;
				}
			}
			
			if (needsEmpty){
				$('.showlist_outer').empty();
				map.empty();
			}
			moment.locale(languageCode);
			var reservationSymbolAdded = false;
			var showcount = 0;
			$.each( msg.shows, function( index, date ){
				var title = $("<h3></h3>");
				var time = moment(index);
				var formatted = time.format("dddd D.M.");
				var nowi = moment().format("dddd D.M.");
				var isToday = nowi == formatted;
				if (onlytoday){
					if (!isToday){
						return;
					}
				}
				title.text(formatted);
				map.append(title);
				var shows = $("<table></table>");
				if (isToday){
					shows.addClass("today");
				} else {
					shows.addClass("future");
				}
				


				if (typeof nexxo_reservations !== 'undefined') {
					shows.attr("data-usereservations", "1");
				}
				$.each( date, function( index, show ){
					showcount++;
					if (showcount > maxshows && maxshows > 0) {
						return;
					}
					var time = moment(show.startTime);
					foundShows = true;
					var row = $("<tr></tr>");
					
					if (showposter || showbanner || showbackground) {
						var postercell = $("<td class='postercell'></td>");
						var poster = $("<img />");
						if (showposter) {
							poster.attr("src",nexxo_showlist.baseurl + "/" + show.posterurl);
						} else if (showbanner) {
							poster.attr("src",nexxo_showlist.baseurl + "/" + show.imgurl);
						} else if (showbackground) {
							poster.attr("src",nexxo_showlist.baseurl + "/" + show.backgroundurl);
						}
						if (linkimage) {
							var imglink = $("<a></a>");
							imglink.attr("href",moviepage+"?movie="+show.movieId+"&location="+_locationid);
							imglink.append(poster);
							postercell.append(imglink);
						} else {
							postercell.append(poster);
						}
						
						row.append(postercell);
					}
					//row.append($("<td></td>").text(time.calendar(null, { sameElse: 'DD.MM. HH:mm'} )));
					var info = $("<td></td>");
					var titlebox = $("<td></td>");
					var movieTitle = $("<h4></h4>");
					var description = $("<p></p>").html(show.intro);
					var movieInfo = $("<p></p>");
					var ageLimit = $("<span></span>");
					ageLimit.addClass("agelimit");
					if (moviepage) {
						var movielink = $("<a></a>");
						movielink.attr("href",moviepage+"?movie="+show.movieId+"&location="+_locationid);
						movielink.text(show.movieTitle);
						movieTitle.append(movielink);
					} else {
						movieTitle.text(show.movieTitle);
					}
					if (show.ageLimit) {
						ageLimit.text(show.ageLimit);
					} else {
						ageLimit.hide();
					}
					var rest = $("<span></span>");
					var hours = Math.floor( show.duration / 60);          
					var minutes = show.duration % 60;
					var duration = hours + " t " + minutes + " min";
					var resttext = duration + ", " + "liput " + show.priceIncludingTax+" €";
					if (showrooms) {
						resttext += " - " + show.roomTitle;
					}
					rest.text(resttext);
					
					movieInfo.append(ageLimit);
					if (show.iconUrl) {
						var icon = jQuery("<img class='categoryicon'>");
						icon.attr("src",show.iconUrl);
						icon.attr("title",show.showTypeTitle);
						icon.attr("alt",show.showTypeTitle);
						movieInfo.append(icon);
					}
					movieInfo.append(rest);
					if (linkmode == 0) {
						info.append(movieTitle);
						if (show.note) {
							info.append(jQuery("<p class='shownote'><strong>"+show.note+"</strong></p>"));
						}
						if (showdescription) {
							info.append(description);
						}
						info.append(movieInfo);
					} else {
						var titlelink = $("<a class='linksurround'></a>");
						titlelink.attr("href",moviepage+"?movie="+show.movieId+"&location="+_locationid);
						if (_layout == "timefirst") {
							titlebox.append(movieTitle);
						} else {
							info.append(movieTitle);
						}
						if (show.note) {
							info.append(jQuery("<p class='shownote'><strong>"+show.note+"</strong></p>"));
						}
						if (showdescription) {
							info.append(description);
						}
						info.append(movieInfo);
						info.append(titlelink);
					}
					var aika = $("<td></td>");
					var disableReservation = 0;
					if (show.reservationMode == 0) {
						disableReservation = 1;
					}
					if (show.disableReservations == 1) {
						disableReservation = 1;
					}
					var dateformat = 'HH:mm';
					if (onlytime) {
						if (linkmode > 1) {
							var timelink = $("<a class='linksurround'></a>");
							timelink.attr("href",moviepage+"?movie="+show.movieId+"&location="+_locationid);
							aika.text(time.format(dateformat));
							aika.append(timelink);
						} else {
							aika.addClass('onlytime');
							aika.text(time.format(dateformat));
						}
					} else {
						aika.text(time.format(nexxo_showlist.dateformat));
					}
					
					
					aika.attr("data-showid",show.showId);
					aika.attr("data-show",show.showId);
					aika.attr("data-movietitle",show.movieTitle);
					aika.attr("data-movie",show.movieId);
					aika.attr("data-maxReservedSeats",show.maxReservedSeats);
					aika.attr("data-paymentmode",show.paymentMode);
					var tim2 = moment(show.startTime);
					aika.attr("data-date",tim2.format(nxt.JsDateFormatForDates));
					aika.attr("data-time",show.klo);
					if (show.reservationsClosingTime) {
						aika.attr("data-reservationsClosingTime",show.reservationsClosingTime);
					}
					aika.attr("data-roomtitle",show.roomTitle);
					aika.attr("data-price",show.priceIncludingTax);
					aika.attr("data-duration",show.duration);
					aika.attr("data-reservationmode",show.reservationMode);
					aika.attr("data-disablereservations",disableReservation);
					aika.addClass("aika");
					aika.addClass("hastime");
				
					if (_layout == "timefirst") {
						row.append(aika);
						row.append(titlebox);
					}
					row.append(info);
					
					if (!reservationSymbolAdded && typeof nexxo_reservations !== 'undefined') {
						reservationSymbolAdded = true;
						var reservationSymbol = $("<div class='reservationsymbol'></div>");
						aika.append(reservationSymbol);
					}
					if (_layout != "timefirst") {
						row.append(aika);
					}
					var colsp = 1;
					//if (showrooms == "1") {
					//	row.append($("<td></td>").text(show.title));
					//}
					if (showprices == "1") {
						row.append($("<td></td>").text(show.priceIncludingTax+"€"));
					}
					shows.append(row);
				});
				map.append(shows);
			});
			if (showcount == 0){
				var noshows = jQuery("<table><tr><td><span class='noshows'>"+nxt.NoShows+"</span></td></tr></table>");
				map.append(noshows);
			}
		}
	 });
})( jQuery );
